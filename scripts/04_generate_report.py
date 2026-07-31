"""
Render output/gaps.json into output/gaps.md: a ranked, human-readable
report with evidence traces and confidence math inline, meant to be read
from live during a defense.

Usage: python scripts/04_generate_report.py
"""
import json
from pathlib import Path

GAPS_PATH = Path("output/gaps.json")
REJECTED_PATH = Path("output/rejected_candidates.jsonl")
ROADMAP_PATH = Path("data/normalized/roadmap.jsonl")
OUT_PATH = Path("output/gaps.md")


def load_jsonl(path):
    return [json.loads(l) for l in open(path)]


def html_url_for(evidence_id, roadmap_by_id):
    rec = roadmap_by_id.get(evidence_id)
    if rec:
        return rec["metadata"].get("html_url")
    return None


def render_gap(gap, roadmap_by_id):
    lines = []
    lines.append(f"## #{gap['rank']} — {gap['need']}")
    lines.append("")
    lines.append(f"**Verdict:** `{gap['verdict']}`  |  **Confidence:** `{gap['confidence']}`")
    lines.append("")
    lines.append(f"> {gap['verdict_justification']}")
    lines.append("")
    lines.append("**Confidence math:**")
    lines.append("")
    lines.append(f"```\n{gap['confidence_justification']}\n```")
    lines.append("")
    lines.append("**Evidence:**")
    lines.append("")
    for e in gap["evidence"]:
        url = html_url_for(e["id"], roadmap_by_id)
        loc = f" ([{e['id']}]({url}))" if url else f" (`{e['id']}`)"
        lines.append(f"- *[{e['weight']}]*{loc}: {e['excerpt_or_paraphrase'].strip()}")
    lines.append("")
    lines.append("**Roadmap cross-references:**")
    lines.append("")
    for ref in gap["roadmap_refs"]:
        url = html_url_for(ref["id"], roadmap_by_id)
        loc = f"[{ref['id']}]({url})" if url else f"`{ref['id']}`"
        lines.append(f"- {loc} — {ref['relation']}")
    lines.append("")
    lines.append(f"**Alternative explanations considered and rejected:** {gap['rejected_alternative_explanations']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def render_rejected(rejected):
    lines = ["## Rejected candidates (falsification log)", "",
             "Candidates that were investigated and did *not* ship, with the specific "
             "disconfirming evidence — included so the room can see what was ruled out, "
             "and why, not just what made the cut.", ""]
    for i, r in enumerate(rejected, start=1):
        lines.append(f"### {i}. {r['need']}")
        lines.append("")
        lines.append(f"**Reason:** {r['reason']}")
        lines.append("")
        if r.get("supporting_evidence_ids"):
            lines.append(f"**Supporting evidence ids:** {', '.join(r['supporting_evidence_ids'])}")
            lines.append("")
    return "\n".join(lines)


def main():
    gaps = json.loads(GAPS_PATH.read_text())
    rejected = load_jsonl(REJECTED_PATH)
    roadmap = load_jsonl(ROADMAP_PATH)
    roadmap_by_id = {r["id"]: r for r in roadmap}

    parts = []
    parts.append("# The Silent Stakeholder — Gap Analysis: Bluesky")
    parts.append("")
    parts.append(
        f"**{len(gaps)} gaps shipped**, ranked strongest evidence first. "
        f"**{len(rejected)} candidates investigated and rejected** via falsification "
        f"(see log below) rather than silently dropped."
    )
    parts.append("")
    parts.append(
        "Source: 8,359 Google Play reviews for Bluesky (2023-04-19 to 2025-04-20) cross-checked "
        "against the live `bluesky-social/social-app` GitHub issue tracker."
    )
    parts.append("")
    parts.append(
        "**Scope note:** the roadmap side of this analysis is unauthenticated-GitHub-API scope: "
        "all currently open issues + all milestones, but **no closed-issue history** (see "
        "Limitations at the bottom). A gap that looks IGNORED or UNDER-PRIORITIZED here could in "
        "principle have a closed, already-merged fix we can't see — each gap's falsification check "
        "is the safeguard against that, not the roadmap scope alone."
    )
    parts.append("")
    parts.append("---")
    parts.append("")

    for gap in gaps:
        parts.append(render_gap(gap, roadmap_by_id))

    parts.append(render_rejected(rejected))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## Limitations for the live defense")
    parts.append("")
    parts.append(
        "- **GitHub roadmap fetched unauthenticated** (no `GITHUB_TOKEN` / `gh auth` available in "
        "this environment): open issues + all milestones only, closed-issue history out of scope. "
        "Logged as a reasoned decision in `logs/filtered.jsonl`, not a silent drop. This means "
        "IGNORED/UNDER-PRIORITIZED verdicts can't distinguish 'nobody filed this' from 'somebody "
        "filed and fixed this, then the issue was closed' — mitigated per-gap by checking whether "
        "review complaint volume itself drops off (a proxy for a real-world fix shipping)."
    )
    parts.append(
        "- **Review corpus ends 2025-04-20**; the GitHub roadmap reflects live state as of the run "
        "date. There's a ~15-month blind window where user sentiment could have shifted on any of "
        "these three gaps without it showing up here."
    )
    parts.append(
        "- **Clustering is deterministic keyword matching**, not an ML/embedding-based semantic "
        "clustering — candidate needs and their roadmap cross-references were identified by manual "
        "reading of the corpus (documented in the pipeline script), which is reproducible and "
        "auditable but will miss paraphrased complaints that don't share the matched keywords."
    )
    parts.append(
        "- **One legitimate-looking candidate was excluded outright**, not scored down: a "
        "moderation-appeals complaint that the corpus expresses almost entirely through partisan "
        "language, which SPEC.md §7 rules out of scope for this exercise."
    )
    parts.append("")

    OUT_PATH.write_text("\n".join(parts))
    print(f"Report written -> {OUT_PATH} ({len(parts)} sections)")


if __name__ == "__main__":
    main()
