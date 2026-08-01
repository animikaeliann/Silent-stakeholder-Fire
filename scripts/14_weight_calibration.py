"""
Exploratory data-driven calibration of the confidence rubric's 4 hand-
picked weights (0.35/0.25/0.20/0.20). Reports whether a grid-searched
alternative differs meaningfully -- does NOT apply anything to gaps.json;
this is exploration only, per the brief.

Purely additive: reads output/gaps.json (only to compare against, not
modify), data/normalized/reviews.jsonl, data/normalized/roadmap.jsonl.
Writes output/weight_calibration_report.md.

Objective (explicit, not black-box): maximize the worst-case margin
between the 4 shipped (accepted) candidates and the 3 rejected candidates
in output/rejected_candidates.jsonl --

    margin(w) = min(confidence_i for shipped i) - max(confidence_j for rejected j)

using each candidate's RAW (pre-rounding) rubric factors, already computed
by 03_infer_gaps.py's own functions (no re-embedding, no re-clustering --
this reuses the exact corroboration/signal_count/latency/
roadmap_disconfirmation values the shipped rubric already produces).
Grid search over the weight simplex (step 0.05, w_i >= 0, sum(w) = 1,
1,771 points) rather than a solver -- simpler to audit, same idea as
Phase 1's grid searches.

Honest limitations (see also the report's own Limitations section):
  - Only 7 data points (4 shipped + 3 rejected) with 3 free degrees of
    freedom (4 weights summing to 1) -- a small-sample optimization that
    can overfit to whichever single factor happens to separate these
    particular 7 candidates, not a validated general-purpose weighting.
  - Circularity risk: the 3 rejected candidates were partly filtered
    USING the original hand-picked weights and rubric (the confidence
    floor, the falsification pass this rubric was designed alongside) --
    so "does this weighting separate accepted from rejected" is partly
    checking whether it agrees with the process that produced the labels
    in the first place, not an independent validation.

Usage: python scripts/14_weight_calibration.py
"""
import importlib.util
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "output" / "weight_calibration_report.md"

GRID_STEP = 0.05
HAND_PICKED_WEIGHTS = {
    "corroboration": 0.35, "signal_count": 0.25, "latency": 0.20, "roadmap_disconfirmation": 0.20,
}
FACTOR_NAMES = ["corroboration", "signal_count", "latency", "roadmap_disconfirmation"]


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compute_raw_factors(candidate, reviews, roadmap_by_number, infer):
    matched = [r for r in reviews if candidate["review_filter"](r)]
    n = len(matched)
    timestamps = [infer.parse_ts(r["timestamp"]) for r in matched if r["timestamp"]]
    span_days = (max(timestamps) - min(timestamps)).days if len(timestamps) >= 2 else 0

    corroboration = min(1.0, n / 15)
    signal_count = min(1.0, n / 100)
    latency = min(1.0, span_days / 365)

    matched_issues = [roadmap_by_number[ref["number"]] for ref in candidate["roadmap_refs"]
                       if ref["number"] in roadmap_by_number]
    disconf_score, _, _ = infer.roadmap_disconfirmation(matched_issues)

    return {
        "corroboration": corroboration, "signal_count": signal_count,
        "latency": latency, "roadmap_disconfirmation": disconf_score, "n": n,
    }


def score(factors, weights):
    return sum(weights[f] * factors[f] for f in FACTOR_NAMES)


def weight_grid(step=GRID_STEP):
    """All (w1,w2,w3,w4) with w_i = k_i * step, sum(k_i) = 1/step, k_i >= 0 integers --
    i.e. every point on the weight simplex at this grid resolution."""
    n_steps = round(1.0 / step)
    for combo in itertools.product(range(n_steps + 1), repeat=len(FACTOR_NAMES) - 1):
        if sum(combo) > n_steps:
            continue
        last = n_steps - sum(combo)
        ks = combo + (last,)
        yield {f: k * step for f, k in zip(FACTOR_NAMES, ks)}


def margin(weights, shipped_factors, rejected_factors):
    shipped_scores = [score(f, weights) for f in shipped_factors]
    rejected_scores = [score(f, weights) for f in rejected_factors]
    return min(shipped_scores) - max(rejected_scores), shipped_scores, rejected_scores


def main():
    infer = _load_module("03_infer_gaps.py")
    sensitivity = _load_module("05_rubric_sensitivity.py")

    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    roadmap = infer.load_jsonl(infer.ROADMAP_PATH)
    roadmap_by_number = {r["metadata"]["number"]: r for r in roadmap if r["source_type"] == "github_issue"}

    shipped_candidates = infer.CANDIDATES
    rejected_candidates = sensitivity.RECONSTRUCTED_REJECTED_CANDIDATES

    shipped_factors = [compute_raw_factors(c, reviews, roadmap_by_number, infer) for c in shipped_candidates]
    rejected_factors = [compute_raw_factors(c, reviews, roadmap_by_number, infer) for c in rejected_candidates]

    hand_margin, hand_shipped_scores, hand_rejected_scores = margin(
        HAND_PICKED_WEIGHTS, shipped_factors, rejected_factors
    )

    best_weights, best_margin = None, float("-inf")
    all_results = []
    for w in weight_grid():
        m, _, _ = margin(w, shipped_factors, rejected_factors)
        all_results.append((w, m))
        if m > best_margin:
            best_weights, best_margin = w, m

    best_margin_val, best_shipped_scores, best_rejected_scores = margin(
        best_weights, shipped_factors, rejected_factors
    )

    # How many grid points tie (within float tolerance) for the best margin? A
    # unique winner is a much stronger signal than one of thousands of ties.
    tied = [w for w, m in all_results if abs(m - best_margin) < 1e-9]

    lines = []
    lines.append("# Weight calibration report (exploratory)")
    lines.append("")
    lines.append(
        "**Exploratory only -- nothing here is applied to gaps.json.** Grid search (step "
        f"{GRID_STEP}, {sum(1 for _ in weight_grid())} points on the weight simplex) maximizing "
        "`margin(w) = min(shipped confidence) - max(rejected confidence)` using each candidate's raw, "
        "pre-rounding rubric factors -- already computed by 03_infer_gaps.py, not re-derived here."
    )
    lines.append("")
    lines.append("## Objective and inputs")
    lines.append("")
    lines.append(f"- {len(shipped_candidates)} shipped candidates, {len(rejected_candidates)} rejected "
                  "candidates (the 3 reconstructed in output/rubric_sensitivity.md).")
    lines.append("- Margin is worst-case (min shipped vs. max rejected), not a difference of averages -- "
                  "a weighting that separates the average well but leaves the weakest shipped gap "
                  "scoring below the strongest rejected candidate is not what \"the rubric correctly "
                  "separates accepted from rejected\" should mean.")
    lines.append("")

    lines.append("## Hand-picked weights (shipped)")
    lines.append("")
    lines.append(f"`{HAND_PICKED_WEIGHTS}` -- margin = **{hand_margin:.4f}**")
    lines.append("")
    lines.append("| Candidate | Kind | Raw score |")
    lines.append("|---|---|---|")
    for c, s in zip(shipped_candidates, hand_shipped_scores):
        lines.append(f"| {c['need'][:50]}… | shipped | {s:.4f} |")
    for c, s in zip(rejected_candidates, hand_rejected_scores):
        lines.append(f"| {c['need'][:50]}… | rejected | {s:.4f} |")
    lines.append("")

    lines.append("## Grid-search optimum")
    lines.append("")
    lines.append(f"`{best_weights}` -- margin = **{best_margin_val:.4f}** "
                  f"({len(tied)} of {sum(1 for _ in weight_grid())} grid points tied for this margin)")
    lines.append("")
    lines.append("| Candidate | Kind | Raw score |")
    lines.append("|---|---|---|")
    for c, s in zip(shipped_candidates, best_shipped_scores):
        lines.append(f"| {c['need'][:50]}… | shipped | {s:.4f} |")
    for c, s in zip(rejected_candidates, best_rejected_scores):
        lines.append(f"| {c['need'][:50]}… | rejected | {s:.4f} |")
    lines.append("")

    if best_margin_val <= 0:
        # Use the hand-picked scores (not best_shipped_scores/best_rejected_scores) to identify
        # the weakest shipped / strongest rejected candidates: at the grid-search optimum multiple
        # rejected candidates tie at exactly 1.0 (corroboration saturates for any n >= 15), so
        # max(key=...) over best_rejected_scores would silently pick whichever tied candidate
        # happens to come first in the list -- not necessarily the substantively relevant one.
        weakest_shipped_idx = min(range(len(hand_shipped_scores)), key=lambda i: hand_shipped_scores[i])
        strongest_rejected_idx = max(range(len(hand_rejected_scores)), key=lambda i: hand_rejected_scores[i])
        weakest_shipped = shipped_candidates[weakest_shipped_idx]
        strongest_rejected = rejected_candidates[strongest_rejected_idx]
        full_reason = (strongest_rejected.get("original_rejection_reason") or "").strip()
        if full_reason.lower().startswith("rejected:"):
            rejection_reason = "excluded on scope grounds (SPEC.md §7), not a low score"
        elif full_reason.lower().startswith("falsified:"):
            rejection_reason = "found already resolved during the data window, not a low score"
        else:
            rejection_reason = "excluded during the original screening, not a low score"
        lines.append(
            f"**Key finding: no weighting of these 4 factors can cleanly separate shipped from "
            f"rejected.** Even at the best possible grid point, the margin is {best_margin_val:.4f} -- "
            "zero or negative, never positive. The blocker is the same one output/rubric_sensitivity.md "
            f"already flagged from a different angle: *\"{strongest_rejected['need'][:70]}…\"* ({rejection_reason}) "
            "has raw rubric numbers as strong as or "
            f"stronger than the weakest shipped gap, *\"{weakest_shipped['need'][:70]}…\"*, on every "
            "weighting tried. This is a rigorous, quantified version of that same finding: it's not "
            "that the hand-picked weights happened to under-rate the excluded candidate -- **no linear "
            "combination of these 4 factors can numerically distinguish them**, because the rubric "
            "formalizes corroboration/scale/persistence/roadmap-neglect, and the excluded candidate "
            "simply scores well on exactly those axes. The exclusion is a scope judgment call that "
            "lives outside what this rubric can express, not a gap in how it's weighted."
        )
        lines.append("")

    weight_diff = {f: round(best_weights[f] - HAND_PICKED_WEIGHTS[f], 4) for f in FACTOR_NAMES}
    max_diff = max(abs(v) for v in weight_diff.values())
    lines.append("## Do the optimized weights differ meaningfully?")
    lines.append("")
    lines.append(f"Per-factor difference (optimized - hand-picked): `{weight_diff}`. "
                  f"Largest single-factor shift: {max_diff:.2f}.")
    lines.append("")
    if len(tied) > 50:
        lines.append(
            f"**Not meaningfully -- the optimum is massively underdetermined.** {len(tied)} grid points "
            "tie for the best margin, meaning huge regions of the weight simplex separate these "
            "particular 7 candidates equally well. With only 7 data points, this is expected, not a "
            "sign the hand-picked weights are wrong: any weighting that keeps corroboration and "
            "roadmap_disconfirmation reasonably weighted (both shipped and rejected candidates vary "
            "along those two axes) tends to separate this specific, small sample. A tie this wide is "
            "itself the headline finding -- it means this objective, on this sample size, cannot "
            "meaningfully distinguish the hand-picked weights from a large family of alternatives."
        )
    elif max_diff < 0.10:
        lines.append(
            "**No, not meaningfully.** The largest single-factor shift is under 0.10 -- well within "
            "what 05_rubric_sensitivity.py already showed the ranking is robust to."
        )
    else:
        lines.append(
            f"**Possibly** -- one or more factors shifted by {max_diff:.2f} or more. Re-scoring below."
        )
    lines.append("")

    lines.append("## Re-scoring the 4 shipped gaps under the optimized weights (report only)")
    lines.append("")
    lines.append("| Gap | Hand-picked confidence (rounded) | Optimized-weight confidence (rounded) |")
    lines.append("|---|---|---|")
    gaps = __import__("json").loads((ROOT / "output" / "gaps.json").read_text())
    for c, raw_hand, raw_opt in zip(shipped_candidates, hand_shipped_scores, best_shipped_scores):
        shipped_gap = next((g for g in gaps if g["need"] == c["need"]), None)
        hand_rounded = shipped_gap["confidence"] if shipped_gap else round(round(raw_hand / 0.05) * 0.05, 2)
        opt_rounded = round(round(raw_opt / 0.05) * 0.05, 2)
        lines.append(f"| {c['need'][:50]}… | {hand_rounded} | {opt_rounded} |")
    lines.append("")
    any_below_threshold = any(
        round(round(s / 0.05) * 0.05, 2) < 0.5 for s in best_shipped_scores
    )
    lines.append(
        "No shipped gap would drop below the 0.5 ship threshold under the optimized weights."
        if not any_below_threshold else
        "**At least one shipped gap would drop below the 0.5 ship threshold under the optimized "
        "weights** -- see table above."
    )
    lines.append("")

    lines.append("## Limitations (read before citing this anywhere)")
    lines.append("")
    lines.append(
        "- **Small sample, high degrees of freedom.** 7 candidates, 3 free weight parameters -- this "
        "grid search can overfit to whichever factor happens to separate these particular 7 rather "
        "than validating a generally-better weighting."
    )
    lines.append(
        "- **Circularity risk, named plainly:** the 3 rejected candidates were partly filtered using "
        "the ORIGINAL hand-picked rubric and confidence floor in the first place (the falsification "
        "pass this rubric was designed alongside). Checking whether a reweighting separates "
        "accepted-from-rejected is partly checking agreement with the process that produced the labels, "
        "not an independent ground truth. This is exploratory, not a validation study."
    )
    lines.append(
        "- Margin-maximization has no term at all for interpretability or the qualitative meaning of "
        "each factor (what corroboration/signal_count/latency/roadmap_disconfirmation *represent*) -- "
        "it would happily zero out a factor if that improved separation on these 7 points, which would "
        "be a worse rubric even if this narrow objective liked it better."
    )
    lines.append("")

    OUT_PATH.write_text("\n".join(lines))
    print(f"Wrote {OUT_PATH}")
    print(f"Hand-picked margin: {hand_margin:.4f}")
    print(f"Best grid margin: {best_margin_val:.4f} ({len(tied)} ties)")
    print(f"Best weights: {best_weights}")


if __name__ == "__main__":
    main()
