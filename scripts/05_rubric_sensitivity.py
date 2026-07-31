"""
Rubric sensitivity / defense-readiness analysis. Purely additive: does NOT
modify output/gaps.json, output/rejected_candidates.jsonl, or re-run
03_infer_gaps.py's main(). It imports 03's candidate definitions and helper
functions (evidence clustering predicates, roadmap_disconfirmation scoring,
parsing) and recomputes confidence deterministically under perturbed rubric
weights, purely for a defense-readiness report.

For the 3 shipped candidates this reuses 03_infer_gaps.CANDIDATES verbatim.
For the 3 pre-rejected candidates (which in 03 only carry a `need` + a
qualitative falsification `reason`, not a full review_filter/roadmap_refs
pair, since they were never scored) this file reconstructs an equivalent
keyword cluster + roadmap cross-reference, deterministically from the same
normalized inputs, so their confidence can be perturbed too. Reconstruction
is documented inline per candidate.

Usage: python scripts/05_rubric_sensitivity.py
"""
import importlib.util
import itertools
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "output" / "rubric_sensitivity.md"


def _load_infer_module():
    path = ROOT / "scripts" / "03_infer_gaps.py"
    spec = importlib.util.spec_from_file_location("infer_gaps_03", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


infer = _load_infer_module()

BASE_WEIGHTS = {
    "corroboration": 0.35,
    "signal_count": 0.25,
    "latency": 0.20,
    "roadmap_disconfirmation": 0.20,
}

# Reconstructed clusters for the 3 pre-rejected candidates, so the rubric's
# behavior can be examined on them too. These predicates/refs were derived
# the same way as 03_infer_gaps.CANDIDATES: deterministic keyword matching
# over data/normalized/reviews.jsonl, verified against the same source data.
RECONSTRUCTED_REJECTED_CANDIDATES = [
    {
        "id": "video-playback-crash",
        "need": infer.PRE_REJECTED[0]["need"],
        "review_filter": lambda r: "crash" in r["text"].lower() and "video" in r["text"].lower(),
        "roadmap_refs": [],  # no adjacent open issue was found for this symptom in the original search
        "original_rejection_reason": infer.PRE_REJECTED[0]["reason"],
    },
    {
        "id": "per-account-post-notifications",
        "need": infer.PRE_REJECTED[1]["need"],
        "review_filter": lambda r: infer.any_has(r["text"], [
            "post notification", "notification for posts from people",
            "turn on notifications for individual", "notifications for individual accounts",
            "notifications for specific accounts", "option for post notifications",
        ]),
        "roadmap_refs": [{"number": 10662, "relation": "bug in an already-shipped per-account "
                                                        "post-notifications feature"}],
        "original_rejection_reason": infer.PRE_REJECTED[1]["reason"],
    },
    {
        "id": "moderation-appeal-transparency",
        "need": infer.PRE_REJECTED[2]["need"],
        "review_filter": lambda r: infer.any_has(r["text"], ["suspend", "appeal"]),
        "roadmap_refs": [],  # no roadmap search was performed for this candidate in the
                             # original pass since it was excluded on non-goal grounds first
        "original_rejection_reason": infer.PRE_REJECTED[2]["reason"],
    },
]

ALL_CANDIDATES = (
    [{**c, "shipped": True, "original_rejection_reason": None} for c in infer.CANDIDATES]
    + [{**c, "shipped": False} for c in RECONSTRUCTED_REJECTED_CANDIDATES]
)


def compute_confidence(candidate, reviews, roadmap_by_number, weights):
    matched_reviews = [r for r in reviews if candidate["review_filter"](r)]
    matched_reviews.sort(key=lambda r: r["timestamp"] or "")
    n = len(matched_reviews)

    timestamps = [infer.parse_ts(r["timestamp"]) for r in matched_reviews if r["timestamp"]]
    span_days = (max(timestamps) - min(timestamps)).days if len(timestamps) >= 2 else 0

    corroboration = min(1.0, n / 15)
    signal_count = min(1.0, n / 100)
    latency = min(1.0, span_days / 365)

    matched_issues = [roadmap_by_number[ref["number"]] for ref in candidate["roadmap_refs"]]
    disconf_score, _, _ = infer.roadmap_disconfirmation(matched_issues)

    raw = (
        weights["corroboration"] * corroboration
        + weights["signal_count"] * signal_count
        + weights["latency"] * latency
        + weights["roadmap_disconfirmation"] * disconf_score
    )
    return round(round(raw / 0.05) * 0.05, 2), n


def perturb_single_factor(base, factor, delta):
    """Bump one weight by delta, rescale the other three proportionally so
    the vector still sums to 1.0."""
    new_val = base[factor] + delta
    if new_val < 0 or new_val > 1:
        return None
    others = [k for k in base if k != factor]
    others_sum = sum(base[k] for k in others)
    remaining = 1.0 - new_val
    scale = remaining / others_sum if others_sum > 0 else 0
    out = {factor: round(new_val, 6)}
    for k in others:
        out[k] = round(base[k] * scale, 6)
    # rounding can leave a residual of a few 1e-6; absorb it into the largest
    # "other" weight so the vector sums to exactly 1.0
    residual = round(1.0 - sum(out.values()), 6)
    largest_other = max(others, key=lambda k: out[k])
    out[largest_other] = round(out[largest_other] + residual, 6)
    return out


def random_perturbations(base, n, seed=42):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        noisy = {k: max(0.01, base[k] + rng.uniform(-0.10, 0.10)) for k in base}
        total = sum(noisy.values())
        normalized = {k: round(v / total, 6) for k, v in noisy.items()}
        residual = round(1.0 - sum(normalized.values()), 6)
        largest = max(normalized, key=lambda k: normalized[k])
        normalized[largest] = round(normalized[largest] + residual, 6)
        out.append(normalized)
    return out


def build_perturbation_set():
    perturbations = {"baseline": dict(BASE_WEIGHTS)}
    for factor in BASE_WEIGHTS:
        for delta in (-0.10, -0.05, 0.05, 0.10):
            w = perturb_single_factor(BASE_WEIGHTS, factor, delta)
            if w is not None:
                perturbations[f"{factor}{'+' if delta > 0 else ''}{delta:+.2f}"] = w
    for i, w in enumerate(random_perturbations(BASE_WEIGHTS, 5), start=1):
        perturbations[f"random-{i}"] = w
    return perturbations


def main():
    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    roadmap = infer.load_jsonl(infer.ROADMAP_PATH)
    roadmap_by_number = {
        r["metadata"]["number"]: r for r in roadmap if r["source_type"] == "github_issue"
    }

    perturbations = build_perturbation_set()

    # results[candidate_id][perturbation_name] = (confidence, n)
    results = {}
    for cand in ALL_CANDIDATES:
        results[cand["id"]] = {}
        for pname, weights in perturbations.items():
            conf, n = compute_confidence(cand, reviews, roadmap_by_number, weights)
            results[cand["id"]][pname] = conf
        results[cand["id"]]["_n"] = n

    shipped_ids = [c["id"] for c in ALL_CANDIDATES if c["shipped"]]
    baseline_order = sorted(shipped_ids, key=lambda cid: results[cid]["baseline"], reverse=True)

    rank_changes = []
    for pname in perturbations:
        order = sorted(shipped_ids, key=lambda cid: results[cid][pname], reverse=True)
        if order != baseline_order:
            rank_changes.append((pname, order))

    threshold_crossings = []
    for cand in ALL_CANDIDATES:
        cid = cand["id"]
        baseline_conf = results[cid]["baseline"]
        baseline_ships = baseline_conf >= 0.5
        for pname in perturbations:
            if pname == "baseline":
                continue
            conf = results[cid][pname]
            ships = conf >= 0.5
            if ships != baseline_ships:
                threshold_crossings.append((cid, pname, baseline_conf, conf, baseline_ships, ships))

    lines = []
    lines.append("# Rubric sensitivity analysis")
    lines.append("")
    lines.append(
        f"Baseline weights: corroboration=0.35, signal_count=0.25, latency=0.20, "
        f"roadmap_disconfirmation=0.20. Perturbed {len(perturbations) - 1} ways: each weight "
        f"individually shifted by ±0.05 and ±0.10 (others rescaled proportionally to keep the "
        f"vector summing to 1.0), plus 5 random weight vectors (seeded, reproducible)."
    )
    lines.append("")
    lines.append("## Headline finding")
    lines.append("")
    if not rank_changes and not threshold_crossings:
        lines.append(
            "**Stable.** Across all "
            f"{len(perturbations) - 1} perturbations, the ranking order of the {len(shipped_ids)} "
            "shipped gaps never changes, and no candidate crosses the 0.5 ship/no-ship threshold "
            "in either direction relative to baseline. The confidence numbers in gaps.json are not "
            "an artifact of the specific weight choice."
        )
    else:
        lines.append(
            f"**Not fully stable.** {len(rank_changes)} perturbation(s) changed the "
            f"{len(shipped_ids)}-gap rank order and {len(threshold_crossings)} threshold-crossing "
            "event(s) were found. See detail below."
        )
    lines.append("")

    lines.append("## Confidence range per candidate across all perturbations")
    lines.append("")
    lines.append("| Candidate | Shipped? | n reviews | Baseline conf. | Min | Max |")
    lines.append("|---|---|---|---|---|---|")
    for cand in ALL_CANDIDATES:
        cid = cand["id"]
        confs = [results[cid][p] for p in perturbations]
        lines.append(
            f"| {cand['need'][:60]}… | {'yes' if cand['shipped'] else 'no'} | "
            f"{results[cid]['_n']} | {results[cid]['baseline']} | {min(confs)} | {max(confs)} |"
        )
    lines.append("")

    lines.append("## Rank-order stability (shipped gaps only)")
    lines.append("")
    lines.append(f"Baseline order: {' > '.join(baseline_order)}")
    lines.append("")
    if rank_changes:
        for pname, order in rank_changes:
            lines.append(f"- **{pname}** flips order to: {' > '.join(order)}")
    else:
        lines.append("No perturbation changed this order.")
    lines.append("")

    lines.append("## Threshold-crossing events (0.5 ship/no-ship line)")
    lines.append("")
    if threshold_crossings:
        for cid, pname, bconf, conf, bships, ships in threshold_crossings:
            lines.append(
                f"- `{cid}` under **{pname}**: confidence {bconf} -> {conf} "
                f"({'ships' if bships else 'rejected'} at baseline, "
                f"{'ships' if ships else 'rejected'} under this perturbation)"
            )
    else:
        lines.append("No candidate crosses the 0.5 line under any tested perturbation.")
    lines.append("")

    lines.append("## Note on the pre-rejected candidates included here")
    lines.append("")
    lines.append(
        "The two falsified candidates (video-playback crash, per-account notifications) were "
        "rejected on evidence-based falsification grounds, not a low confidence score -- their "
        "rubric confidence here is for sensitivity testing only and does not mean they should "
        "ship; the falsification evidence (documented in output/rejected_candidates.jsonl) "
        "stands independently of this analysis."
    )
    mod = next(c for c in ALL_CANDIDATES if c["id"] == "moderation-appeal-transparency")
    mod_conf = results["moderation-appeal-transparency"]["baseline"]
    lines.append(
        f"The moderation-appeal-transparency candidate scores {mod_conf} confidence under the "
        f"baseline rubric ({'above' if mod_conf >= 0.5 else 'below'} the 0.5 ship line) using a "
        "reconstructed cluster and no roadmap match (roadmap_disconfirmation=1.0, since no "
        "search for an adjacent issue was performed before it was excluded). This candidate was "
        "excluded on SPEC.md §7 non-goal grounds (confounded with partisan sentiment), "
        "independent of what the rubric alone would say -- a reminder that the rubric formalizes "
        "corroboration/scale/persistence/roadmap-neglect, not scope-fit, and a human judgment "
        "call is still load-bearing on top of it."
    )
    lines.append("")

    OUT_PATH.write_text("\n".join(lines))
    print(f"Wrote {OUT_PATH}")
    print(f"Rank changes: {len(rank_changes)}, threshold crossings: {len(threshold_crossings)}")


if __name__ == "__main__":
    main()
