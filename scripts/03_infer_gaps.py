"""
Gap inference pipeline (SPEC.md full loop): ingest normalized reviews +
roadmap -> cluster signals -> candidate gap -> cross-check against roadmap
-> score confidence -> adversarial falsification check -> accept/reject.

All clustering/matching here is deterministic keyword matching over the
normalized corpus, and all candidate needs + their matching roadmap issue
numbers were identified by direct manual reading of the data in this
session (see conversation) -- there is no external LLM call anywhere in
this pipeline, per SPEC's "no external API" constraint on gap inference.

Usage: python scripts/03_infer_gaps.py
"""
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REVIEWS_PATH = Path("data/normalized/reviews.jsonl")
ROADMAP_PATH = Path("data/normalized/roadmap.jsonl")
GAPS_OUT = Path("output/gaps.json")
REJECTED_OUT = Path("output/rejected_candidates.jsonl")

TODAY = datetime(2026, 7, 31, tzinfo=timezone.utc)
STALE_DAYS = 180


def parse_ts(ts):
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def load_jsonl(path):
    return [json.loads(l) for l in open(path)]


def any_has(text, words):
    t = text.lower()
    return any(w in t for w in words)


# ---------------------------------------------------------------------------
# Candidate definitions. Each candidate's review_filter selects the evidence
# cluster (a python predicate over a normalized review record); roadmap_refs
# are the specific open-issue numbers found to be adjacent to the need,
# identified by manually searching data/normalized/roadmap.jsonl for the
# relevant subject matter and reading each issue body in full.
# ---------------------------------------------------------------------------

CANDIDATES = [
    {
        "id": "login-keyboard-dismissal",
        "need": "Users can't sign in or join the waitlist because the on-screen "
                "keyboard flashes open and immediately closes on the "
                "username/password/email field, blocking account access "
                "entirely on some Android devices.",
        "review_filter": lambda r: "keyboard" in r["text"].lower() and any_has(
            r["text"], ["log", "sign", "password", "username", "waitlist", "wait list"]
        ),
        "roadmap_refs": [
            {"number": 6264, "relation": "exact match: same symptom (login field keyboard "
                                          "opens then closes/deselects on Android), same repro steps"},
            {"number": 2371, "relation": "adjacent-narrower: same class of Android keyboard/input "
                                         "bug, but scoped to composer handle-input, not the login screen"},
        ],
        "alt_explanation": "Could this be device fragmentation noise (one bad OEM keyboard) rather "
                            "than a real product gap? Ruled out: reports name Samsung Galaxy S8/S20/S22/S24 "
                            "and Pixel 6a across Android 9 through 14, spanning 6 dot releases of the app "
                            "over two years -- a single-device explanation does not fit a defect this wide "
                            "or this durable.",
    },
    {
        "id": "no-private-account-remove-follower",
        "need": "Users have no way to stop bot/spam accounts from following them: there is "
                "no private/locked account option, and no way to remove an unwanted follower "
                "without blocking them.",
        "review_filter": lambda r: any_has(r["text"], [
            "private account", "make my account private", "make account private",
            "lock my account", "locked account", "make your account private",
            "account private", "remove a follower", "remove follower",
            "remove unwanted follower", "remove individual", "private/locked",
        ]),
        "roadmap_refs": [
            {"number": 1155, "relation": "exact match: request for private/locked accounts"},
            {"number": 1160, "relation": "exact match: request for ability to remove a follower "
                                         "without blocking"},
        ],
        "alt_explanation": "Could this just be generic anti-spam sentiment rather than a specific, "
                            "buildable feature ask? Ruled out: the review text converges on two concrete, "
                            "named feature requests (account privacy toggle, follower removal) that already "
                            "match filed, multi-hundred-comment GitHub issues -- this is not vague "
                            "dissatisfaction, it is a request the team has already scoped.",
    },
    {
        "id": "follower-count-block-desync",
        "need": "Follower counts and follower lists don't reflect reality: blocked accounts "
                "still count as followers and still appear in follower lists, and displayed "
                "follower counts are simply inconsistent/wrong on refresh.",
        "review_filter": lambda r: (
            any_has(r["text"], ["follower count is", "follower count incorrect", "says i have",
                                "followers but only", "followers but it only", "follower count"])
            or ("blocked" in r["text"].lower() and "follow" in r["text"].lower()
                and any_has(r["text"], ["still", "count"]))
        ),
        "roadmap_refs": [
            {"number": 853, "relation": "exact match: blocked accounts still counted/shown as followers"},
            {"number": 7370, "relation": "exact match: follower count displays incorrect/inconsistent number"},
        ],
        "alt_explanation": "Could this be the same underlying need as the private-account gap above, "
                            "just double-counted? Ruled out: this cluster reports a data-integrity bug "
                            "(the number/list is factually wrong) rather than a missing privacy control "
                            "(no way to prevent following in the first place) -- different roadmap issues, "
                            "different fixes, kept as a separate gap. Only 1 review overlaps between the "
                            "two evidence sets.",
    },
    {
        "id": "captcha-blocks-signup-login",
        "need": "A broken CAPTCHA/verification step blocks account creation and login for a "
                "significant share of users: it fails to render, times out with a gateway error, "
                "or rejects a correctly-completed challenge with an 'invalid verification code' error.",
        "review_filter": lambda r: any_has(r["text"], [
            "captcha", "recaptcha", "not a robot", "i am a robot", "am i a robot",
        ]),
        "roadmap_refs": [
            {"number": 6704, "relation": "exact match: sign-up captcha fails to display correctly on some "
                                          "Android devices (foldables/tablets), preventing completion"},
            {"number": 6936, "relation": "exact match: captcha fails to render during account creation on web"},
        ],
        "alt_explanation": "Could this just be users failing the challenge (user error) rather than a real "
                            "bug? Ruled out: reports describe specific technical failure modes -- 'bad "
                            "gateway, upstream timeout, upstream failure', the prompt rendering cut off on "
                            "foldable/tablet displays, and 'invalid verification code' errors appearing "
                            "immediately after a challenge is correctly completed, not after a wrong answer; "
                            "one reviewer reports the team acknowledged this as 'a known problem' that "
                            "'hasn't been fixed'. Could this double-count the shipped login-keyboard-"
                            "dismissal gap? Ruled out by checking directly: zero review-id overlap between "
                            "the two keyword clusters, and the failure modes are unrelated (keyboard focus "
                            "vs. captcha rendering/validation). Device/platform diversity across the cluster "
                            "(Android app, Chrome/Safari incognito web, Samsung Galaxy Fold, tablets) rules "
                            "out single-device fragmentation as the explanation.",
    },
]

# Candidates considered and explicitly rejected via falsification, documented
# up front because the falsification check (not a threshold miss) is why they
# don't ship -- see each "reason" for the specific disconfirming evidence.
PRE_REJECTED = [
    {
        "need": "App crashes every time a user tries to open/play a video (full-screen or inline).",
        "reason": "falsified: resolved during the data window. 30 independent complaints cluster "
                  "tightly between 2024-12-23 and 2025-01-21 (traceable to a 'December 20 update' named "
                  "in-review), then reviews from 2025-01-21 onward explicitly say the crash is fixed "
                  "('Fixed the issue I had with videos crashing the app', 'Thank you for finally fixing "
                  "the video crashing') and complaint volume drops to ~0/month afterward. Shipping this "
                  "as a live gap would mislead the room into re-litigating an already-fixed bug.",
        "evidence_ids": ["review-play-05618", "review-play-06529", "review-play-06841"],
    },
    {
        "need": "Users want the ability to turn on notifications for individual accounts' new posts.",
        "reason": "falsified: feature appears to already exist. The ask (review-play-06244, "
                  "review-play-06302, both 2025-01) matches a per-account 'post notifications' feature "
                  "that a much later open bug, github-issue-10662 ('Post notifications override "
                  "notifications for replies/quotes', updated 2026-05-30), describes as already live and "
                  "malfunctioning -- i.e. the feature request was fulfilled; what remains is a narrower "
                  "bug, not this gap.",
        "evidence_ids": ["review-play-06244", "review-play-06302", "github-issue-10662"],
    },
    {
        "need": "Accounts get suspended/labeled with no explanation or a slow/absent appeal process.",
        "reason": "rejected: signal is confounded with partisan sentiment about moderation policy "
                  "('anti free speech', 'liberal wet dream', 'gas chamber for Republicans'). SPEC.md "
                  "§7 rules this project out as a sentiment dashboard and requires seeing 'both sides' -- "
                  "the narrower, legitimately actionable complaint (opaque/slow appeals) cannot be cleanly "
                  "separated from the political framing in this corpus without editorializing about which "
                  "moderation decisions were correct, so it is left out rather than shipped on a shaky "
                  "corroboration count.",
        "evidence_ids": ["review-play-04433", "review-play-04966", "review-play-05830"],
    },
]


def roadmap_disconfirmation(matched_issues):
    """Score how much the roadmap fails to address the need, plus per-issue reasons.
    Returns (score in [0,1], list[str] reasons, verdict tag)."""
    if not matched_issues:
        return 1.0, ["no adjacent roadmap issue found"], "IGNORED"

    per_issue_scores = []
    all_reasons = []
    for iss in matched_issues:
        m = iss["metadata"]
        created = parse_ts(m["created_at"])
        updated = parse_ts(m["updated_at"])
        age_created_days = (TODAY - created).days if created else 0
        age_updated_days = (TODAY - updated).days if updated else 0
        has_milestone = m.get("milestone") is not None
        labels = m.get("labels") or []

        if m["state"] == "closed" and m.get("state_reason") == "not_planned":
            per_issue_scores.append(0.9)
            all_reasons.append(f"#{m['number']}: closed as not_planned (explicitly deprioritized)")
        elif not has_milestone and age_updated_days > STALE_DAYS:
            per_issue_scores.append(0.8)
            all_reasons.append(
                f"#{m['number']}: no milestone AND stale ({age_updated_days}d since last update, "
                f"threshold {STALE_DAYS}d)"
            )
        elif not has_milestone and age_created_days > 365:
            per_issue_scores.append(0.65)
            all_reasons.append(
                f"#{m['number']}: open {age_created_days}d ({age_created_days // 365}y+) and never "
                f"scheduled to a milestone, despite recent comment activity"
            )
        elif not labels:
            per_issue_scores.append(0.55)
            all_reasons.append(f"#{m['number']}: unlabeled (labels == [])")
        elif not has_milestone:
            per_issue_scores.append(0.45)
            all_reasons.append(f"#{m['number']}: no milestone yet (recently opened)")
        else:
            per_issue_scores.append(0.15)
            all_reasons.append(f"#{m['number']}: has milestone, actively scheduled")

    score = round(sum(per_issue_scores) / len(per_issue_scores), 4)
    verdict = "UNDER-PRIORITIZED"
    return score, all_reasons, verdict


def evidence_diversity_ok(evidence):
    """SPEC.md §3 hard rule: no gap ships with fewer than 2 evidence entries
    from at least 2 distinct source_types."""
    if len(evidence) < 2:
        return False
    distinct_types = set()
    for e in evidence:
        eid = e["id"]
        if eid.startswith("review-"):
            distinct_types.add("review")
        elif eid.startswith("github-issue-"):
            distinct_types.add("github_issue")
        elif eid.startswith("github-milestone-"):
            distinct_types.add("github_milestone")
        elif eid.startswith("ticket-"):
            distinct_types.add("ticket")
    return len(distinct_types) >= 2


def build_gap(candidate, reviews, roadmap_by_number, rank):
    matched_reviews = [r for r in reviews if candidate["review_filter"](r)]
    matched_reviews.sort(key=lambda r: r["timestamp"] or "")
    n = len(matched_reviews)

    timestamps = [parse_ts(r["timestamp"]) for r in matched_reviews if r["timestamp"]]
    span_days = (max(timestamps) - min(timestamps)).days if len(timestamps) >= 2 else 0

    corroboration = round(min(1.0, n / 15), 4)          # saturates fast: "is this real"
    signal_count = round(min(1.0, n / 100), 4)           # saturates slow: "how big is this"
    latency = round(min(1.0, span_days / 365), 4)        # 1yr+ persistence = max

    matched_issues = [roadmap_by_number[ref["number"]] for ref in candidate["roadmap_refs"]]
    disconf_score, disconf_reasons, verdict = roadmap_disconfirmation(matched_issues)

    confidence_raw = (
        0.35 * corroboration + 0.25 * signal_count + 0.20 * latency + 0.20 * disconf_score
    )
    confidence = round(round(confidence_raw / 0.05) * 0.05, 2)

    justification = (
        f"corroboration={corroboration} (n={n} distinct reviews / 15 cap) * 0.35 = "
        f"{round(0.35 * corroboration, 4)}; "
        f"signal_count={signal_count} (n={n} / 100 cap) * 0.25 = {round(0.25 * signal_count, 4)}; "
        f"latency={latency} (span={span_days}d / 365 cap) * 0.20 = {round(0.20 * latency, 4)}; "
        f"roadmap_disconfirmation={disconf_score} * 0.20 = {round(0.20 * disconf_score, 4)}. "
        f"Sum={round(confidence_raw, 4)} -> rounded to nearest 0.05 = {confidence}. "
        f"Disconfirmation basis: {'; '.join(disconf_reasons)}."
    )

    # Evidence: at least 2 entries, at least 2 distinct source_types (review + github_issue).
    evidence = []
    if matched_reviews:
        primary = max(matched_reviews, key=lambda r: len(r["text"]))
        evidence.append({
            "id": primary["id"],
            "excerpt_or_paraphrase": primary["text"][:280],
            "weight": "primary",
        })
        others = [r for r in matched_reviews if r["id"] != primary["id"]]
        if others:
            corroborating_review = others[len(others) // 2]
            evidence.append({
                "id": corroborating_review["id"],
                "excerpt_or_paraphrase": corroborating_review["text"][:280],
                "weight": "corroborating",
            })
    for iss in matched_issues:
        evidence.append({
            "id": iss["id"],
            "excerpt_or_paraphrase": iss["text"][:280].replace("\n", " "),
            "weight": "corroborating",
        })

    assert evidence_diversity_ok(evidence), "hard rule violated: evidence diversity"

    verdict_justification = (
        f"{n} independent reviews ({matched_reviews[0]['timestamp'][:10]} to "
        f"{matched_reviews[-1]['timestamp'][:10]}) describe this need. "
        + "; ".join(disconf_reasons)
    )

    gap = {
        "rank": rank,
        "need": candidate["need"],
        "confidence": confidence,
        "confidence_justification": justification,
        "verdict": verdict,
        "verdict_justification": verdict_justification,
        "evidence": evidence,
        "roadmap_refs": [
            {"id": f"github-issue-{ref['number']}", "relation": ref["relation"]}
            for ref in candidate["roadmap_refs"]
        ],
        "rejected_alternative_explanations": candidate["alt_explanation"],
    }
    return gap, n, confidence


def main():
    reviews = load_jsonl(REVIEWS_PATH)
    roadmap = load_jsonl(ROADMAP_PATH)
    roadmap_by_number = {
        r["metadata"]["number"]: r for r in roadmap if r["source_type"] == "github_issue"
    }

    rejected = []
    for pr in PRE_REJECTED:
        rejected.append({
            "need": pr["need"],
            "reason": pr["reason"],
            "supporting_evidence_ids": pr["evidence_ids"],
        })

    accepted = []
    for candidate in CANDIDATES:
        gap, n, confidence = build_gap(candidate, reviews, roadmap_by_number, rank=0)
        if confidence < 0.5:
            rejected.append({
                "need": candidate["need"],
                "reason": f"below confidence threshold: computed confidence {confidence} < 0.5. "
                          f"{gap['confidence_justification']}",
                "supporting_evidence_ids": [e["id"] for e in gap["evidence"]],
            })
            continue
        accepted.append(gap)

    accepted.sort(key=lambda g: g["confidence"], reverse=True)
    for i, g in enumerate(accepted, start=1):
        g["rank"] = i

    GAPS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(GAPS_OUT, "w") as f:
        json.dump(accepted, f, indent=2)

    with open(REJECTED_OUT, "w") as f:
        for rec in rejected:
            f.write(json.dumps(rec) + "\n")

    print(f"Accepted gaps: {len(accepted)} -> {GAPS_OUT}")
    for g in accepted:
        print(f"  #{g['rank']} [{g['verdict']}] conf={g['confidence']}  {g['need'][:70]}")
    print(f"Rejected candidates: {len(rejected)} -> {REJECTED_OUT}")
    for r in rejected:
        print(f"  - {r['need'][:70]} -- {r['reason'][:80]}")


if __name__ == "__main__":
    main()
