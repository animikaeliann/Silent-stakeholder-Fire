"""
Draft a notification email per routed gap. Purely additive: reads
output/gaps.json and output/team_routing.json, writes
output/team_notifications/gap_{rank}_{team}.{txt,json}. Does not modify
gaps.json, gaps.md, or team_routing.json.

Every field in the draft is derived from data already in gaps.json/
team_routing.json (need text, confidence math, evidence, roadmap refs,
routing reasoning) -- nothing here is invented per-gap; the only
gap-specific human authorship is SHORT_TOPIC_OVERRIDES, a few words of
subject-line phrasing for the 3 currently-shipped gaps, with a mechanical
fallback for any future gap that isn't in that dict.

Usage: python scripts/08_draft_notifications.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAPS_PATH = ROOT / "output" / "gaps.json"
ROUTING_PATH = ROOT / "output" / "team_routing.json"
OUT_DIR = ROOT / "output" / "team_notifications"
REPO_URL = "https://github.com/bluesky-social/social-app"

# Short, human-written subject-line topics for the gaps currently in
# gaps.json. A future gap not listed here falls back to a mechanical
# truncation of its `need` text -- see topic_for().
SHORT_TOPIC_OVERRIDES = {
    1: "Login keyboard-dismissal bug blocks sign-in",
    2: "No private-account / remove-follower controls against bot spam",
    3: "Follower count / block-list desync",
}

NEXT_STEP_BY_VERDICT = {
    "IGNORED": "Consider triaging this as a new roadmap item -- right now nothing in the "
               "tracker addresses it at all.",
    "UNDER-PRIORITIZED": "Consider adding this to the next milestone planning pass; it's "
                         "already been filed and/or discussed but has gone unscheduled.",
    "MISUNDERSTOOD": "Consider clarifying scope with the reporting users or reframing the "
                     "existing related issue -- it currently appears to solve an adjacent but "
                     "different problem.",
}


def topic_for(gap):
    if gap["rank"] in SHORT_TOPIC_OVERRIDES:
        return SHORT_TOPIC_OVERRIDES[gap["rank"]]
    words = gap["need"].split()
    return " ".join(words[:8]) + ("…" if len(words) > 8 else "")


def n_reviews_from_justification(justification):
    m = re.search(r"n=(\d+) distinct reviews", justification)
    return int(m.group(1)) if m else None


def milestone_phrase(justification):
    if "no milestone" in justification.lower():
        return "no roadmap milestone"
    if "closed as not_planned" in justification.lower():
        return "explicitly deprioritized"
    return "roadmap status unclear"


def one_line_confidence_reason(justification):
    """Name the top-weighted-contribution factor(s) from the rubric math string."""
    contributions = {}
    for factor in ("corroboration", "signal_count", "latency", "roadmap_disconfirmation"):
        m = re.search(rf"{factor}=\d+\.\d+.*?\*\s*[\d.]+\s*=\s*(\d+\.\d+)", justification)
        if m:
            contributions[factor] = float(m.group(1))
    if not contributions:
        return "see full rubric math below"
    ranked = sorted(contributions.items(), key=lambda x: -x[1])
    top = ranked[0][0].replace("_", " ")
    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < 0.03:
        second = ranked[1][0].replace("_", " ")
        return f"driven jointly by {top} and {second}"
    return f"driven mainly by {top}"


def evidence_url(evidence_id):
    m = re.match(r"^github-issue-(\d+)$", evidence_id)
    if m:
        return f"{REPO_URL}/issues/{m.group(1)}"
    return None


def build_draft(gap, routing_rec):
    n = n_reviews_from_justification(gap["confidence_justification"])
    subject = (
        f"[Gap Analysis] {topic_for(gap)} -- "
        f"{n if n is not None else '?'} user reports, {milestone_phrase(gap['confidence_justification'])}"
    )

    evidence_lines = []
    for e in gap["evidence"][:3]:
        url = evidence_url(e["id"])
        loc = f"{e['id']} ({url})" if url else e["id"]
        evidence_lines.append(f"- [{e['weight']}] {e['excerpt_or_paraphrase'][:180].strip()} -- {loc}")

    roadmap_lines = []
    for ref in gap["roadmap_refs"]:
        url = evidence_url(ref["id"])
        loc = f"{ref['id']} ({url})" if url else ref["id"]
        roadmap_lines.append(f"- {loc} -- {ref['relation']}")

    next_step = NEXT_STEP_BY_VERDICT.get(gap["verdict"], "Consider reviewing this against current priorities.")
    conf_reason = one_line_confidence_reason(gap["confidence_justification"])

    team = routing_rec["team"]
    cc_teams = routing_rec.get("cc_teams", [])

    body_lines = [
        f"To: {team.lower().replace('_', '-')}@bluesky-social-app.internal (simulated demo address)",
    ]
    if cc_teams:
        body_lines.append(
            f"Cc: {', '.join(t.lower().replace('_', '-') for t in cc_teams)}"
            f"@bluesky-social-app.internal (near-tie routing, see below)"
        )
    body_lines += [
        f"Subject: {subject}",
        "",
        f"Hi {team.replace('_', ' ').title()} team,",
        "",
        gap["need"],
        "",
        f"Confidence: {gap['confidence']} ({conf_reason})",
        f"Verdict: {gap['verdict']}",
        "",
        "Evidence:",
        *evidence_lines,
        "",
        "Related roadmap issue(s):",
        *roadmap_lines,
        "",
        f"Suggested next step: {next_step}",
        "",
        f"Why this was routed to {team}:",
        routing_rec["reasoning"],
        "",
        "--",
        "Generated by The Silent Stakeholder gap-analysis pipeline. This is a draft for",
        "human review before sending -- see output/team_notifications/README.md for how",
        "(and whether) it actually gets sent.",
    ]
    text = "\n".join(body_lines)

    structured = {
        "gap_rank": gap["rank"],
        "team": team,
        "cc_teams": cc_teams,
        "to_address": f"{team.lower().replace('_', '-')}@bluesky-social-app.internal",
        "cc_addresses": [f"{t.lower().replace('_', '-')}@bluesky-social-app.internal" for t in cc_teams],
        "subject": subject,
        "confidence": gap["confidence"],
        "verdict": gap["verdict"],
        "need": gap["need"],
        "evidence": gap["evidence"][:3],
        "roadmap_refs": gap["roadmap_refs"],
        "suggested_next_step": next_step,
        "routing_reasoning": routing_rec["reasoning"],
        "body_text": text,
    }
    return text, structured


def main():
    gaps = json.loads(GAPS_PATH.read_text())
    routing_records = json.loads(ROUTING_PATH.read_text())
    routing = {r["gap_rank"]: r for r in routing_records}
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    written = []
    for gap in gaps:
        routing_rec = routing[gap["rank"]]
        text, structured = build_draft(gap, routing_rec)
        team_slug = routing_rec["team"].lower()
        txt_path = OUT_DIR / f"gap_{gap['rank']}_{team_slug}.txt"
        json_path = OUT_DIR / f"gap_{gap['rank']}_{team_slug}.json"
        txt_path.write_text(text)
        json_path.write_text(json.dumps(structured, indent=2))
        written.append((txt_path, json_path))

    print(f"Wrote {len(written)} draft(s) to {OUT_DIR}")
    for txt_path, json_path in written:
        print(f"  {txt_path.name}, {json_path.name}")


if __name__ == "__main__":
    main()
