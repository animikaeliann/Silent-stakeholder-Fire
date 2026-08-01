"""
Phase 3 of the latent/second-order signal mining work: run the ONE
candidate that survived Phase 2's synthesis (output/latent_candidates.md)
through the SAME rigor pipeline used for gaps 1-4 -- reuses
03_infer_gaps.py's build_gap()/roadmap_disconfirmation()/
evidence_diversity_ok() unchanged, does not reimplement the rubric.

Numbered 18, not 17: script 17 is reserved for the (separate, paused)
scripts/17_sync_to_db.py DB-persistence-layer work, so as not to collide
with it when that work resumes.

This is a REPORT-ONLY pass. It does NOT write to output/gaps.json or
output/gaps.md, and does not change what's shipped -- any decision to
ship this (or not) comes back to a human, same as the CAPTCHA gap and
every other candidate this project has ever proposed. Purely additive:
reads data/normalized/reviews.jsonl, data/normalized/roadmap.jsonl.
Writes output/latent_candidates_scored.json.

New field beyond the standard gap-object contract: `latent_justification`
-- separate from and in addition to `confidence_justification`. A
candidate without a defensible answer here does not proceed regardless of
confidence score, since scoring high on the existing rubric doesn't by
itself prove a need is second-order rather than stated -- those are
different properties, and this phase's whole premise is that the 4
shipped gaps already score well on the FIRST property without clearing
the second.

Usage: python scripts/18_latent_scoring.py
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "output" / "latent_candidates_scored.json"

EVIDENCE_REVIEW_IDS = {
    "review-play-00687", "review-play-01857", "review-play-06630", "review-play-08298",
}

CANDIDATE = {
    "id": "persistent-read-state",
    "need": (
        "Bluesky has no persistent \"where you left off\" state anywhere in the app -- "
        "not in the main feed, not in the following feed, not in notifications -- so "
        "reopening the app, backgrounding it, or refreshing always lands on the newest "
        "content with no way to resume reading from where the user stopped."
    ),
    "review_filter": lambda r: r["id"] in EVIDENCE_REVIEW_IDS,
    "roadmap_refs": [
        {"number": 7238, "relation": "closest match: 'Reverse chronological / catch up view "
                                      "(with pinch of \"mark as read\"?)' -- a resumable-reading "
                                      "feature request that would directly address the feed/"
                                      "following-feed half of this need"},
        {"number": 5089, "relation": "adjacent: 'Auto-refetch on tab focus' -- a live-refresh "
                                      "feature request adjacent to the notification-refresh half "
                                      "of this need, though phrased for the web client"},
    ],
    "alt_explanation": (
        "Could this simply be three separate, minor UX nitpicks (following-feed scroll "
        "memory, notification refresh, main-feed scroll memory) rather than one underlying "
        "gap? Considered, and not fully resolved here -- Phase 2's own synthesis "
        "(output/latent_candidates.md) discloses this exact tension rather than asserting "
        "it away. What supports treating them as one gap: all three describe the identical "
        "missing capability (persisting a \"last seen\" position across sessions/refreshes) "
        "applied to three different surfaces of the same app, and two of the four reviews "
        "explicitly invoke the same competitor (Twitter) as the implicit baseline being "
        "missed. What weighs against it: n=4 is thin, and no single review connects all "
        "three symptoms itself -- a skeptical reader could reasonably keep them separate. "
        "This candidate is being scored, not shipped, specifically so the rubric's numbers "
        "(especially the low corroboration count at this n) can weigh in on this open "
        "question rather than resting on narrative judgment alone."
    ),
}

LATENT_JUSTIFICATION = (
    "Each of the 4 supporting reviews is, individually, a plainly-stated complaint -- a "
    "reader would understand any ONE of them immediately (e.g. review-play-06630: \"it "
    "needs to remember where you left off\"). What is NOT stated anywhere is the "
    "connection between the three symptoms (notification refresh, following-feed "
    "position, main-feed position) as one underlying architectural gap -- no review "
    "names more than one of these three surfaces, and nothing in the corpus uses a "
    "shared keyword across them (\"notification\" vs. \"following feed\" vs. \"feed\" "
    "share no vocabulary Detector 1/2's pattern matching would connect on its own). This "
    "pattern spans 19 months (2023-09 to 2025-04) without ever being clustered together "
    "by the keyword-based pipeline that shipped gaps 1-4, which is itself evidence the "
    "connection isn't obvious from a normal read of the corpus -- a judge skimming even a "
    "generous \"loudest 20 reviews\" sample (dominated by the volume-heavy shipped themes: "
    "keyboard dismissal, CAPTCHA, moderation/political content, crashes) would be very "
    "unlikely to encounter enough of these four thin, scattered, differently-worded "
    "reviews to notice the cross-cutting pattern. Disclosed honestly: this is a real "
    "tension, not a settled case -- see output/latent_candidates.md's full discussion, "
    "including the counter-argument that this may just be three separately-obvious "
    "requests given one label after the fact."
)


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    infer = _load_module("03_infer_gaps.py")

    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    roadmap = infer.load_jsonl(infer.ROADMAP_PATH)
    roadmap_by_number = {r["metadata"]["number"]: r for r in roadmap if r["source_type"] == "github_issue"}

    # Reuses 03_infer_gaps.py's build_gap() UNCHANGED -- same rubric, same
    # falsification-adjacent evidence-diversity hard rule, same roadmap
    # disconfirmation scoring used for gaps 1-4. rank=None marks this as a
    # candidate, not a shipped rank -- nothing here implies a 5th shipped gap.
    gap, n, confidence = infer.build_gap(CANDIDATE, reviews, roadmap_by_number, rank=None)

    scored = dict(gap)
    scored["candidate_id"] = CANDIDATE["id"]
    scored["latent_justification"] = LATENT_JUSTIFICATION
    scored["ships_by_confidence_alone"] = confidence >= 0.5

    output = {
        "note": (
            "REPORT ONLY. Not applied to output/gaps.json or output/gaps.md. Any decision "
            "to ship this as gap #5 requires explicit human approval, same as every other "
            "candidate this project has proposed."
        ),
        "phase_2_survivor_count": 1,
        "candidates": [scored],
    }

    OUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote {OUT_PATH}")
    print(f"Candidate: {CANDIDATE['id']}")
    print(f"  n={n}, confidence={confidence}, ships_by_confidence_alone={scored['ships_by_confidence_alone']}")
    print(f"  verdict={gap['verdict']}")


if __name__ == "__main__":
    main()
