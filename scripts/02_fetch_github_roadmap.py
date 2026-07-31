"""
Fetch issues and milestones for bluesky-social/social-app from the GitHub
REST API, save raw responses to data/raw/, then normalize into the schema
locked in SPEC.md §2 at data/normalized/roadmap.jsonl.

Auth strategy (resolved without a token being available in this environment):
  1. If GITHUB_TOKEN is set, use it.
  2. Else if `gh auth token` succeeds (gh CLI logged in), use that.
  3. Else proceed unauthenticated at the public 60 req/hr core rate limit.

When unauthenticated, this script fetches OPEN issues only (skips closed-
issue history) and ALL milestones (cheap, low page count), to stay inside
the unauthenticated rate limit within one run. That scope reduction is
logged to logs/filtered.jsonl as an explicit, reasoned decision, not a
silent drop.

The issues endpoint returns PRs too; those are dropped (roadmap = issues,
not code changes) and the drop is logged to logs/filtered.jsonl, same
convention as 01_normalize_reviews.py.

Usage: python scripts/02_fetch_github_roadmap.py
"""
import http.client
import json
import os
import subprocess
import time
from pathlib import Path
import urllib.request
import urllib.error

REPO = "bluesky-social/social-app"
API = "https://api.github.com"

ISSUES_OUT = Path("data/raw/github_issues.json")
MILESTONES_OUT = Path("data/raw/github_milestones.json")
NORMALIZED_OUT = Path("data/normalized/roadmap.jsonl")
FILTERED_LOG = Path("logs/filtered.jsonl")
DATASET_NAME = "github_roadmap_bluesky-social/social-app"

MIN_REMAINING_TO_CONTINUE = 2  # stop paginating before we hit the wall


def resolve_token():
    env_token = os.environ.get("GITHUB_TOKEN")
    if env_token:
        return env_token, "GITHUB_TOKEN env var"
    try:
        out = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip(), "gh auth token"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None, None


def gh_get(url, token):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    attempts = 5
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req) as resp:
                link = resp.headers.get("Link", "")
                remaining = int(resp.headers.get("X-RateLimit-Remaining", "0"))
                reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                body = json.loads(resp.read())
                return body, link, remaining, reset
        except urllib.error.HTTPError as e:
            if e.code == 403 and attempt < attempts - 1:
                time.sleep(5)
                continue
            raise
        except (http.client.IncompleteRead, ConnectionError, urllib.error.URLError, TimeoutError) as e:
            if attempt < attempts - 1:
                print(f"    transient network error ({e!r}), retrying ({attempt + 1}/{attempts})...")
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"failed after retries: {url}")


def paginate_all(path_qs, token, filtered_sink, source_label):
    url = f"{API}{path_qs}"
    items = []
    page = 0
    truncated = False
    while url:
        body, link, remaining, reset = gh_get(url, token)
        items.extend(body)
        page += 1
        print(f"  page {page}: +{len(body)} (total {len(items)}), rate remaining {remaining}")

        if remaining <= MIN_REMAINING_TO_CONTINUE:
            next_url = None
            for part in link.split(","):
                part = part.strip()
                if part.endswith('rel="next"'):
                    next_url = part[part.index("<") + 1 : part.index(">")]
            if next_url:
                truncated = True
                filtered_sink.append({
                    "stage": "fetch_github_roadmap",
                    "reason": "rate_limit_truncation",
                    "detail": f"{source_label}: stopped after page {page} with only {remaining} "
                              f"requests remaining (unauthenticated 60/hr cap); reset at {reset}.",
                })
                print(f"  !! stopping early: only {remaining} rate-limit requests left")
            break

        next_url = None
        for part in link.split(","):
            part = part.strip()
            if part.endswith('rel="next"'):
                next_url = part[part.index("<") + 1 : part.index(">")]
        url = next_url
    return items, truncated


def fetch_issues(token, authed, filtered):
    state = "all" if authed else "open"
    print(f"Fetching issues (state={state})...")
    raw, truncated = paginate_all(
        f"/repos/{REPO}/issues?state={state}&per_page=100&sort=created&direction=asc",
        token, filtered, "issues",
    )

    issues, dropped_prs = [], []
    for item in raw:
        if "pull_request" in item:
            dropped_prs.append({"stage": "fetch_github_roadmap", "reason": "is_pull_request", "id": item["number"], "url": item["html_url"]})
        else:
            issues.append(item)

    ISSUES_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(ISSUES_OUT, "w") as f:
        json.dump(issues, f)

    filtered.extend(dropped_prs)

    if not authed:
        filtered.append({
            "stage": "fetch_github_roadmap",
            "reason": "out_of_scope_no_auth",
            "detail": "closed-issue history skipped: no GitHub auth available (GITHUB_TOKEN "
                      "unset, gh CLI not logged in), proceeding unauthenticated per time "
                      "constraints. Only open issues + all milestones were fetched. Roadmap "
                      "gap-analysis coverage below is therefore biased toward currently-open "
                      "work and cannot see issues resolved-then-closed in the past.",
        })

    print(f"Issues: {len(issues)} kept -> {ISSUES_OUT}")
    print(f"PRs dropped from issues feed: {len(dropped_prs)} -> logged to {FILTERED_LOG}")
    return issues, truncated


def fetch_milestones(token, filtered):
    print("Fetching milestones (state=all)...")
    milestones, truncated = paginate_all(
        f"/repos/{REPO}/milestones?state=all&per_page=100", token, filtered, "milestones"
    )
    MILESTONES_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(MILESTONES_OUT, "w") as f:
        json.dump(milestones, f)
    print(f"Milestones: {len(milestones)} -> {MILESTONES_OUT}")
    return milestones, truncated


def normalize(issues, milestones):
    normalized = []

    for it in issues:
        labels = [l["name"] if isinstance(l, dict) else l for l in it.get("labels", [])]
        milestone = it.get("milestone")
        body = it.get("body") or ""
        normalized.append({
            "id": f"github-issue-{it['number']}",
            "source_type": "github_issue",
            "source_dataset": DATASET_NAME,
            "text": f"{it['title']}\n\n{body}".strip(),
            "timestamp": it.get("created_at"),
            "rating": None,
            "metadata": {
                "number": it["number"],
                "state": it["state"],
                "state_reason": it.get("state_reason"),
                "labels": labels,
                "milestone": milestone["title"] if milestone else None,
                "created_at": it.get("created_at"),
                "updated_at": it.get("updated_at"),
                "closed_at": it.get("closed_at"),
                "comments": it.get("comments"),
                "html_url": it.get("html_url"),
            },
        })

    for m in milestones:
        desc = m.get("description") or ""
        normalized.append({
            "id": f"github-milestone-{m['number']}",
            "source_type": "github_milestone",
            "source_dataset": DATASET_NAME,
            "text": f"{m['title']}\n\n{desc}".strip(),
            "timestamp": m.get("created_at"),
            "rating": None,
            "metadata": {
                "number": m["number"],
                "state": m["state"],
                "due_on": m.get("due_on"),
                "open_issues": m.get("open_issues"),
                "closed_issues": m.get("closed_issues"),
                "html_url": m.get("html_url"),
            },
        })

    NORMALIZED_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(NORMALIZED_OUT, "w") as f:
        for rec in normalized:
            f.write(json.dumps(rec) + "\n")

    print(f"Normalized: {len(normalized)} records -> {NORMALIZED_OUT}")
    return normalized


def main():
    token, token_source = resolve_token()
    authed = token is not None
    if authed:
        print(f"Authenticated via {token_source}.")
    else:
        print("No GitHub auth available (GITHUB_TOKEN unset, gh CLI not logged in). "
              "Proceeding unauthenticated: open issues + all milestones only.")

    filtered = []
    issues, issues_truncated = fetch_issues(token, authed, filtered)
    milestones, milestones_truncated = fetch_milestones(token, filtered)

    FILTERED_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(FILTERED_LOG, "a") as f:
        for rec in filtered:
            f.write(json.dumps(rec) + "\n")

    normalize(issues, milestones)

    open_n = sum(1 for i in issues if i["state"] == "open")
    closed_n = sum(1 for i in issues if i["state"] == "closed")
    print(f"\nSummary: {open_n} open / {closed_n} closed issues, {len(milestones)} milestones")
    if issues_truncated or milestones_truncated:
        print("NOTE: fetch was truncated by rate limit before completing all pages.")


if __name__ == "__main__":
    main()
