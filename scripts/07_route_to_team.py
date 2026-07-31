"""
Team-routing classifier for shipped gaps. Purely additive: reads
output/gaps.json and data/normalized/roadmap.jsonl, writes
output/team_routing.json. Does not modify gaps.json, gaps.md, or any
previously committed pipeline output.

Classification uses two signals, in priority order:
  (a) GitHub labels on the gap's roadmap_refs issues, mapped through
      LABEL_TEAM_MAP -- checked first, since a label like "area:moderation"
      or "platform:android" would be a stronger, human-curated signal than
      keyword guessing.
  (b) Keyword matching over the gap's `need` text + its evidence excerpts,
      scored per team via KEYWORD_TEAM_MAP -- used whenever (a) yields
      nothing informative.

On this specific dataset, (a) is checked and reported per gap but is a
non-factor: the roadmap was fetched unauthenticated (see
scripts/02_fetch_github_roadmap.py) and bluesky-social/social-app's issue
labels are limited to `bug`, `feature-request`, and workflow-status tags
(`x:planned`, `x:discussing`, `x:on-the-roadmap`, `x:wontfix`, ...) -- there
is no area/platform taxonomy on the referenced issues (#6264, #2371, #1155,
#1160, #853, #7370 all confirmed empty or generic). So (b) drives every
classification here; this is stated explicitly per gap in the reasoning
output rather than silently falling through, since "why did you route this
to backend" needs a real, checkable answer.

Usage: python scripts/07_route_to_team.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAPS_PATH = ROOT / "output" / "gaps.json"
ROADMAP_PATH = ROOT / "data" / "normalized" / "roadmap.jsonl"
OUT_PATH = ROOT / "output" / "team_routing.json"

TEAMS = ["WEB_FRONTEND", "BACKEND_API", "MOBILE_CLIENT", "TRUST_SAFETY", "INFRA_PLATFORM", "UNCLEAR"]

# (a) Label -> team. Populated defensively for labels that COULD appear on a
# roadmap with a richer taxonomy than this dataset happens to have; see
# module docstring for what's actually present here.
LABEL_TEAM_MAP = {
    "platform:android": "MOBILE_CLIENT",
    "platform:ios": "MOBILE_CLIENT",
    "area:mobile": "MOBILE_CLIENT",
    "area:moderation": "TRUST_SAFETY",
    "area:trust-safety": "TRUST_SAFETY",
    "area:web": "WEB_FRONTEND",
    "area:frontend": "WEB_FRONTEND",
    "area:api": "BACKEND_API",
    "area:backend": "BACKEND_API",
    "area:infra": "INFRA_PLATFORM",
    "area:platform": "INFRA_PLATFORM",
}

# (b) Team -> keywords to match (case-insensitive substring) against the
# gap's need text + evidence excerpts. Order matters only for tie display;
# scoring counts every match per team independently.
KEYWORD_TEAM_MAP = {
    "MOBILE_CLIENT": [
        "keyboard", "android", "samsung", "pixel", "ios", "app crash", "app crashes",
        "sign in", "sign-in", "login", "log in", "on-screen keyboard", "mobile device",
        "phone", "tablet",
    ],
    "TRUST_SAFETY": [
        "bot", "spam", "moderation", "suspended", "suspend", "appeal", "private account",
        "block", "harassment", "abuse", "trust", "safety", "labeled", "report", "unwanted follower",
    ],
    "BACKEND_API": [
        "notification", "api", "sync", "count is", "count incorrect", "data integrity",
        "server", "backend", "database", "webhook", "endpoint", "inconsistent",
    ],
    "WEB_FRONTEND": [
        "ui", "button", "screen", "layout", "css", "web app", "browser", "scroll", "display",
        "render", "web browser", "desktop",
    ],
    "INFRA_PLATFORM": [
        "outage", "rate limit", "deploy", "infrastructure", "downtime", "latency", "uptime",
        "server error", "500 error", "timeout",
    ],
}


def load_jsonl(path):
    return [json.loads(l) for l in open(path)]


def label_signal(gap, roadmap_by_id):
    """Check (a): labels on this gap's roadmap_refs issues."""
    checked_issues = []
    for ref in gap["roadmap_refs"]:
        rec = roadmap_by_id.get(ref["id"])
        labels = rec["metadata"].get("labels", []) if rec else []
        checked_issues.append({"id": ref["id"], "labels": labels})
        for label in labels:
            if label in LABEL_TEAM_MAP:
                return LABEL_TEAM_MAP[label], label, checked_issues
    return None, None, checked_issues


NEED_TEXT_WEIGHT = 2   # a match in the curated need statement counts more than
EVIDENCE_TEXT_WEIGHT = 1  # a match in a raw, possibly multi-topic evidence excerpt
NEAR_TIE_MARGIN = 1    # scores within this margin of the top score are "also plausible"


def keyword_signal(gap):
    """Check (b): weighted keyword scoring. Need-statement matches count more
    than evidence-excerpt matches, since evidence excerpts are raw review text
    that often bundles unrelated complaints in the same snippet."""
    need_text = gap["need"].lower()
    evidence_text = " ".join(e["excerpt_or_paraphrase"].lower() for e in gap["evidence"])

    scores = {}
    matched_terms = {}
    for team, keywords in KEYWORD_TEAM_MAP.items():
        need_hits = [kw for kw in keywords if kw in need_text]
        evidence_hits = [kw for kw in keywords if kw in evidence_text]
        score = NEED_TEXT_WEIGHT * len(need_hits) + EVIDENCE_TEXT_WEIGHT * len(evidence_hits)
        if score > 0:
            scores[team] = score
            matched_terms[team] = sorted(set(need_hits) | set(evidence_hits))
    if not scores:
        return "UNCLEAR", {}, matched_terms, []

    ordered = sorted(scores.items(), key=lambda x: -x[1])
    best_team, best_score = ordered[0]
    also_plausible = [t for t, s in ordered[1:] if best_score - s <= NEAR_TIE_MARGIN]
    return best_team, scores, matched_terms, also_plausible


def classify(gap, roadmap_by_id):
    label_team, matched_label, checked_issues = label_signal(gap, roadmap_by_id)
    if label_team:
        reasoning = (
            f"Routed via GitHub label signal: issue label '{matched_label}' on one of this gap's "
            f"roadmap_refs maps to {label_team} per LABEL_TEAM_MAP."
        )
        return label_team, reasoning, "label", []

    kw_team, scores, matched_terms, also_plausible = keyword_signal(gap)
    label_summary = "; ".join(
        f"{ci['id']}: labels={ci['labels'] or '[]'}" for ci in checked_issues
    )
    if kw_team == "UNCLEAR":
        reasoning = (
            f"No informative GitHub label found on referenced issues ({label_summary}). "
            "No keyword match against any team's vocabulary either -- routed to UNCLEAR as the "
            "documented fallback rather than guessing."
        )
    else:
        score_summary = ", ".join(f"{t}={s}" for t, s in sorted(scores.items(), key=lambda x: -x[1]))
        reasoning = (
            f"No informative GitHub label found on referenced issues ({label_summary}) -- fell back "
            f"to weighted keyword matching (need-statement matches count {NEED_TEXT_WEIGHT}x, "
            f"evidence-excerpt matches count {EVIDENCE_TEXT_WEIGHT}x, since evidence excerpts are raw "
            f"review text that often bundles unrelated complaints in the same snippet). Matched terms "
            f"for {kw_team}: {matched_terms[kw_team]}. Full score breakdown across all teams: "
            f"{score_summary}."
        )
        if also_plausible:
            verb = "is" if len(also_plausible) == 1 else "are"
            reasoning += (
                f" NOTE -- near-tie: {', '.join(also_plausible)} scored within {NEAR_TIE_MARGIN} "
                f"point(s) of the winning team and {verb} also a defensible primary owner for this "
                "gap; treat this as cross-cutting rather than a confident single-team call."
            )
    return kw_team, reasoning, "keyword", also_plausible


def main():
    gaps = json.loads(GAPS_PATH.read_text())
    roadmap = load_jsonl(ROADMAP_PATH)
    roadmap_by_id = {r["id"]: r for r in roadmap}

    routing = []
    for gap in gaps:
        team, reasoning, signal_used, also_plausible = classify(gap, roadmap_by_id)
        routing.append({
            "gap_rank": gap["rank"],
            "need": gap["need"],
            "team": team,
            "cc_teams": also_plausible,
            "signal_used": signal_used,
            "reasoning": reasoning,
        })

    OUT_PATH.write_text(json.dumps(routing, indent=2))
    print(f"Wrote {OUT_PATH}")
    for r in routing:
        print(f"  #{r['gap_rank']} -> {r['team']} (via {r['signal_used']}): {r['need'][:60]}")


if __name__ == "__main__":
    main()
