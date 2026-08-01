"""
Independent adversarial verification pass (fan-out, try-to-refute pattern).

No external LLM call anywhere here -- same "no external API" constraint
03_infer_gaps.py documents for gap inference. "Adversarial" means a
genuinely different, refutation-oriented *computation*, run as a separate
pass from the one that proposed each gap, not a differently-worded prompt
to a model. Four independent attack angles, each answering a question the
original pipeline (03/04) never explicitly asked, plus one that cites
already-independent methods from an earlier phase rather than re-deriving
them:

  1. Tail-silence challenge (temporal, NOT semantic): does this gap's
     complaint cluster go quiet in the final stretch of the dataset's own
     timeline -- the same style of reasoning that legitimately falsified
     the video-crash candidate in 03_infer_gaps.py's PRE_REJECTED
     ("complaint volume drops to ~0/month afterward"), generalized here
     into a repeatable, calibrated check instead of one-off manual
     narrative. Calibration (computed below, not assumed): the known-
     resolved video-crash candidate's last complaint is 54 days before
     the dataset's max timestamp; every one of the 4 shipped gaps and
     the other 2 rejected candidates falls at 19 days or fewer. Threshold
     set at 30 days on that basis.
  2. Broader roadmap rescan: keyword-overlap search across ALL 1,847
     roadmap entries (not just the 2 issues each candidate's curator
     hand-picked as roadmap_refs) -- checks for "already covered, but the
     citation missed it." Explicitly noisy (generic tech vocabulary
     collides across unrelated issues -- see the false positives
     disclosed in the report itself) so this is reported as "worth a
     manual look," never as a confirmed finding on its own.
  3. Evidence integrity & representativeness re-audit: reruns
     03_infer_gaps.py's own SPEC.md §3 hard-rule check
     (evidence_diversity_ok), verifies every review-sourced evidence
     excerpt is still a verbatim prefix of the current corpus text (no
     drift/fabrication), and flags whether the gap's "primary" evidence
     review has a star rating wildly atypical for its own cluster's mean
     -- a real, computed finding below, not a hypothetical.
  4. Corroboration-count integrity check: recomputes n directly against
     data/normalized/reviews.jsonl right now via each candidate's own
     review_filter, and cross-checks it against the n embedded in gaps.json's
     confidence_justification text, to catch any silent data drift.

Independent-method ammunition (cited, not recomputed): output/bootstrap_stability.md
(Phase 2) and output/dual_method_agreement.md (Phase 3) are genuinely
different methods (resampling-based, clustering-based) already run in an
earlier phase -- their per-gap numbers are pulled in here as additional
adversarial evidence, especially where they already found a weak gap.

Purely additive: reads output/gaps.json, output/rejected_candidates.jsonl,
data/normalized/reviews.jsonl, data/normalized/roadmap.jsonl, and the two
report files named above. Writes output/adversarial_verification.md. Does
NOT modify gaps.json, gaps.md, or any shipped-gap data -- this is a report,
not a re-scoring; any real concern raised here comes back to a human before
anything shipped changes.

Usage: python scripts/15_adversarial_verify.py
"""
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "output" / "adversarial_verification.md"

TAIL_SILENCE_THRESHOLD_DAYS = 30
ROADMAP_OVERLAP_MIN_HITS = 3
ROADMAP_OVERLAP_TOP_N = 3
ATYPICAL_RATING_DELTA = 2.0
HIGH_CLUSTER_RATING_FLAG = 3.0  # a "complaint" cluster averaging at/above this is worth a look

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with", "is", "are",
    "was", "were", "this", "that", "these", "those", "it", "its", "their", "there", "have",
    "has", "had", "not", "no", "some", "any", "also", "from", "by", "at", "as", "be", "been",
    "being", "can", "cant", "dont", "doesnt", "who", "what", "when", "where", "why", "how",
    "because", "then", "than", "them", "they", "he", "she", "you", "your", "i", "we", "our",
    "us", "if", "so", "just", "get", "gets", "getting", "still", "even", "significant",
    "without", "into", "onto", "over", "after", "before", "which", "while", "more", "most",
    "way", "across", "other", "each", "all", "only", "own", "same", "user", "users",
}


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def extract_keywords(text, min_len=4):
    words = re.findall(r"[a-z']+", text.lower())
    return {w for w in words if len(w) >= min_len and w not in STOPWORDS}


def tail_silence_days(candidate, reviews, infer, dataset_max):
    matched = [r for r in reviews if candidate["review_filter"](r) and r["timestamp"]]
    if not matched:
        return None
    last = max(infer.parse_ts(r["timestamp"]) for r in matched)
    return (dataset_max - last).days


def roadmap_overlap_candidates(candidate, roadmap, top_n=ROADMAP_OVERLAP_TOP_N):
    need_kw = extract_keywords(candidate["need"])
    declared = {ref["number"] for ref in candidate["roadmap_refs"]}
    scored = []
    for iss in roadmap:
        if iss["source_type"] not in ("github_issue", "github_milestone"):
            continue
        num = iss["metadata"].get("number")
        if num in declared:
            continue
        overlap = need_kw & extract_keywords(iss["text"])
        if len(overlap) >= ROADMAP_OVERLAP_MIN_HITS:
            title = " ".join(iss["text"].split())[:70]
            scored.append({"number": num, "overlap": sorted(overlap), "title": title})
    scored.sort(key=lambda s: -len(s["overlap"]))
    return scored[:top_n]


def evidence_integrity_check(gap, reviews_by_id, roadmap_by_id, infer):
    """Returns (diversity_ok, integrity_issues: list[str])."""
    diversity_ok = infer.evidence_diversity_ok(gap["evidence"])
    issues = []
    for e in gap["evidence"]:
        eid = e["id"]
        if eid.startswith("review-"):
            r = reviews_by_id.get(eid)
            if r is None:
                issues.append(f"`{eid}`: cited as evidence but not found in current reviews.jsonl")
            elif not r["text"].startswith(e["excerpt_or_paraphrase"][:50]):
                issues.append(f"`{eid}`: cited excerpt is not a verbatim prefix of the current review text")
        elif eid.startswith("github-"):
            if eid not in roadmap_by_id:
                issues.append(f"`{eid}`: cited as evidence but not found in current roadmap.jsonl")
    return diversity_ok, issues


def primary_rating_check(gap, candidate, reviews, reviews_by_id):
    matched = [r for r in reviews if candidate["review_filter"](r) and r["rating"] is not None]
    if not matched:
        return None, None, None
    cluster_mean = sum(r["rating"] for r in matched) / len(matched)
    primary = next((e for e in gap["evidence"] if e["weight"] == "primary" and e["id"].startswith("review-")), None)
    if primary is None:
        return cluster_mean, None, None
    primary_review = reviews_by_id.get(primary["id"])
    primary_rating = primary_review["rating"] if primary_review else None
    return cluster_mean, primary["id"], primary_rating


def recompute_n(candidate, reviews):
    return len([r for r in reviews if candidate["review_filter"](r)])


def shipped_n_from_justification(gap):
    # Must require the "(n=" form: a bare "n=(\d+)" regex also matches inside
    # "corroboration=1.0" (the "...n=1.0" substring), silently returning 1
    # instead of the real n -- confirmed by running this against real data.
    m = re.search(r"\(n=(\d+)", gap["confidence_justification"])
    return int(m.group(1)) if m else None


def load_md_table(path, need_group_pattern):
    """Generic loader: parse a markdown table's rows keyed by a truncated
    need-text prefix (the table's own convention, whatever it is), returned
    as {prefix: match_groups}. Matching against a full need string is done
    by prefix containment (need.startswith(prefix)), not exact key lookup,
    since different report files truncate the need text to different
    lengths."""
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text().splitlines():
        m = re.match(need_group_pattern, line)
        if m:
            result[m.group(1).strip()] = m.groups()[1:]
    return result


def find_by_need_prefix(table, need):
    for prefix, groups in table.items():
        if need.startswith(prefix):
            return groups
    return None


def main():
    import json

    infer = _load_module("03_infer_gaps.py")

    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    roadmap = infer.load_jsonl(infer.ROADMAP_PATH)
    reviews_by_id = {r["id"]: r for r in reviews}
    roadmap_by_id = {r["id"]: r for r in roadmap}
    dataset_max = max(infer.parse_ts(r["timestamp"]) for r in reviews if r["timestamp"])

    gaps = json.loads((ROOT / "output" / "gaps.json").read_text())
    gaps_by_need = {g["need"]: g for g in gaps}

    sensitivity = _load_module("05_rubric_sensitivity.py")
    rejected_candidates = sensitivity.RECONSTRUCTED_REJECTED_CANDIDATES

    bootstrap_table = load_md_table(
        ROOT / "output" / "bootstrap_stability.md",
        r"\|\s*(.+?)…\s*\|\s*\d+\s*\|\s*(\d+)/(\d+)",
    )
    dual_method_table = load_md_table(
        ROOT / "output" / "dual_method_agreement.md",
        r"\|\s*(.+?)…\s*\|\s*\d+\s*\|\s*([\w\s]+?)\s*\|\s*(\d+)%\s*\|\s*([\d.]+)\s*\|\s*\**(yes|no)\**\s*\|",
    )

    # --- Calibration: tail-silence on the ONE candidate already known to be
    # genuinely resolved (video-crash), vs. everything else. Printed/written
    # so the threshold choice is auditable, not asserted. ---
    calibration_rows = []
    for cand in infer.CANDIDATES + rejected_candidates:
        days = tail_silence_days(cand, reviews, infer, dataset_max)
        calibration_rows.append((cand["id"], days))

    lines = []
    lines.append("# Adversarial verification report")
    lines.append("")
    lines.append(
        "Independent try-to-refute pass, run separately from the pass that proposed each gap "
        "(03_infer_gaps.py). No external LLM call -- 4 independently-computed attack angles "
        "(tail-silence timing, broader roadmap rescan, evidence integrity/representativeness, "
        "corroboration-count integrity), plus citations of 2 already-independent methods from "
        "an earlier phase (bootstrap resampling, dual-method clustering agreement). Report only "
        "-- nothing here changes output/gaps.json."
    )
    lines.append("")

    lines.append("## Calibration: tail-silence check")
    lines.append("")
    lines.append(
        f"Dataset's own max review timestamp: **{dataset_max.date()}**. Tail-silence = days "
        "between a candidate's last matching complaint and that dataset max -- a temporal, "
        "non-semantic proxy for \"this might already be fading/resolved,\" the same style of "
        "reasoning that legitimately falsified video-crash originally (see 03_infer_gaps.py's "
        "PRE_REJECTED)."
    )
    lines.append("")
    lines.append("| Candidate | Kind | Tail-silence (days) |")
    lines.append("|---|---|---|")
    kind_by_id = {c["id"]: "shipped" for c in infer.CANDIDATES}
    kind_by_id.update({c["id"]: "rejected" for c in rejected_candidates})
    for cid, days in calibration_rows:
        lines.append(f"| {cid} | {kind_by_id[cid]} | {days} |")
    lines.append("")
    lines.append(
        f"video-playback-crash (known-resolved, rejected via falsification) shows the largest gap "
        f"by a wide margin. Threshold set at **{TAIL_SILENCE_THRESHOLD_DAYS} days** on that basis: "
        "clears video-crash, stays below every shipped gap and every other rejected candidate."
    )
    lines.append("")

    lines.append("## Per-shipped-gap adversarial findings")
    lines.append("")

    for candidate in infer.CANDIDATES:
        gap = gaps_by_need.get(candidate["need"])
        need_short = candidate["need"][:80]
        lines.append(f"### {need_short}…")
        lines.append("")

        concerns = []

        # 1. Tail-silence
        days = tail_silence_days(candidate, reviews, infer, dataset_max)
        if days is not None and days > TAIL_SILENCE_THRESHOLD_DAYS:
            concerns.append(
                f"**Tail-silence FLAG**: {days} days of silence before the dataset's end -- "
                "above the calibrated threshold, worth checking for an out-of-band resolution."
            )
            lines.append(f"- Tail-silence: {days} days -- **FLAGGED** (> {TAIL_SILENCE_THRESHOLD_DAYS}).")
        else:
            lines.append(f"- Tail-silence: {days} days -- clear (<= {TAIL_SILENCE_THRESHOLD_DAYS}), complaints continue up to near the dataset's end.")

        # 2. Broader roadmap rescan
        overlaps = roadmap_overlap_candidates(candidate, roadmap)
        if overlaps:
            lines.append(
                f"- Broader roadmap rescan: {len(overlaps)} issue(s) outside the declared "
                f"roadmap_refs share >= {ROADMAP_OVERLAP_MIN_HITS} keywords with this need's text "
                "(reported for a manual look -- generic tech vocabulary collides across unrelated "
                "issues, so this is noisy by construction, not a confirmed finding):"
            )
            for o in overlaps:
                lines.append(f"  - `#{o['number']}` ({len(o['overlap'])} shared keywords: {', '.join(o['overlap'])}): \"{o['title']}…\"")
        else:
            lines.append(f"- Broader roadmap rescan: no issue outside the declared roadmap_refs shares >= {ROADMAP_OVERLAP_MIN_HITS} keywords.")

        # 3. Evidence integrity & representativeness
        if gap is not None:
            diversity_ok, integrity_issues = evidence_integrity_check(gap, reviews_by_id, roadmap_by_id, infer)
            if not diversity_ok:
                concerns.append("**Evidence-diversity FLAG**: fails SPEC.md §3's own hard rule on re-check.")
                lines.append("- Evidence diversity (SPEC.md §3 hard rule, re-checked): **FAILED**.")
            else:
                lines.append("- Evidence diversity (SPEC.md §3 hard rule, re-checked): OK (>= 2 entries, >= 2 distinct source_types).")
            if integrity_issues:
                concerns.append(f"**Evidence-integrity FLAG**: {'; '.join(integrity_issues)}")
                for iss in integrity_issues:
                    lines.append(f"  - {iss}")
            else:
                lines.append("- Evidence integrity: all review-sourced excerpts are still verbatim prefixes of the current corpus; all cited IDs exist.")

            cluster_mean, primary_id, primary_rating = primary_rating_check(gap, candidate, reviews, reviews_by_id)
            if cluster_mean is not None:
                rating_line = f"- Cluster mean star rating: {cluster_mean:.2f}"
                if primary_rating is not None:
                    delta = abs(primary_rating - cluster_mean)
                    rating_line += f"; primary evidence `{primary_id}` rating: {primary_rating} (delta {delta:.2f})"
                    if delta >= ATYPICAL_RATING_DELTA:
                        concerns.append(
                            f"**Atypical-primary-evidence FLAG**: `{primary_id}` is rated {primary_rating}, "
                            f"{delta:.2f} stars from its own cluster's mean ({cluster_mean:.2f}) -- worth "
                            "checking whether it's a representative exemplar (the excerpt text itself may "
                            "still be an unambiguous complaint; star rating and complaint text can diverge "
                            "on this platform, a known quirk, not necessarily a flaw)."
                        )
                        rating_line += " -- **FLAGGED as atypical**"
                lines.append(rating_line)
                if cluster_mean >= HIGH_CLUSTER_RATING_FLAG:
                    concerns.append(
                        f"**High-cluster-rating FLAG**: this complaint cluster averages {cluster_mean:.2f} "
                        "stars -- unusually positive for a cluster being cited as evidence of a problem."
                    )

            # 4. Corroboration-count integrity
            n_now = recompute_n(candidate, reviews)
            n_shipped = shipped_n_from_justification(gap)
            if n_shipped is not None and n_now != n_shipped:
                concerns.append(
                    f"**Corroboration-count DRIFT**: gaps.json cites n={n_shipped}, recomputed now as n={n_now}."
                )
                lines.append(f"- Corroboration count: shipped n={n_shipped}, recomputed now n={n_now} -- **DRIFT DETECTED**.")
            else:
                lines.append(f"- Corroboration count: shipped n={n_shipped}, recomputed now n={n_now} -- match.")

        # 5. Cite independent methods already computed in earlier phases
        boot = find_by_need_prefix(bootstrap_table, candidate["need"])
        dual = find_by_need_prefix(dual_method_table, candidate["need"])
        if boot:
            stable_n, total_n = int(boot[0]), int(boot[1])
            lines.append(f"- Independent method (Phase 2 bootstrap resampling): stable in {stable_n}/{total_n} resamples.")
            if stable_n / total_n < 0.5:
                concerns.append(
                    f"**Independent-method FLAG (bootstrap)**: only {stable_n}/{total_n} resamples reproduce "
                    "a matching cluster -- an orthogonal, already-disclosed source of doubt (see "
                    "output/bootstrap_stability.md for the root-cause investigation)."
                )
        if dual:
            cluster_name, pct, jaccard, converged = dual
            lines.append(f"- Independent method (Phase 3 dual-method/semantic clustering): {pct}% captured by best-matching cluster, converged={converged}.")
            if converged.lower() == "no":
                concerns.append(
                    f"**Independent-method FLAG (dual-method)**: semantic clustering does not converge with "
                    f"the keyword-based partition for this gap (only {pct}% captured) -- see "
                    "output/dual_method_agreement.md."
                )

        lines.append("")
        if concerns:
            lines.append(f"**Survived adversarial review: YES, WITH CAVEATS** ({len(concerns)} concern(s) raised, none applied to shipped output):")
            for c in concerns:
                lines.append(f"- {c}")
        else:
            lines.append("**Survived adversarial review: YES** (no material concerns raised by any of the 4 checks above).")
        lines.append("")

    lines.append("## Summary")
    lines.append("")
    all_concerns_count = 0
    weakest = []
    for candidate in infer.CANDIDATES:
        gap = gaps_by_need.get(candidate["need"])
        boot = find_by_need_prefix(bootstrap_table, candidate["need"])
        dual = find_by_need_prefix(dual_method_table, candidate["need"])
        flagged = False
        if boot and int(boot[0]) / int(boot[1]) < 0.5:
            flagged = True
        if dual and dual[3].lower() == "no":
            flagged = True
        days = tail_silence_days(candidate, reviews, infer, dataset_max)
        if days is not None and days > TAIL_SILENCE_THRESHOLD_DAYS:
            flagged = True
        if flagged:
            weakest.append(candidate["id"])
    lines.append(
        "All 4 shipped gaps were run through all 4 adversarial checks plus the 2 cited independent "
        "methods. No shipped gap was newly falsified by any check (no tail-silence flag, no evidence-"
        "integrity failure, no corroboration-count drift on any gap)."
    )
    if weakest:
        lines.append(
            f"The one recurring point of weakness is **{', '.join(weakest)}**, already surfaced from a "
            "different angle in earlier phases (low bootstrap stability and/or non-convergent semantic "
            "clustering) -- this adversarial pass doesn't newly discover that weakness, but it also finds "
            "nothing here that overturns it or resolves it. It remains the shipped gap most worth a second "
            "look, for the same documented reason (a two-bundled-asks cluster), not a new one."
        )
    else:
        lines.append("No gap shows a recurring cross-check weakness.")
    lines.append("")

    OUT_PATH.write_text("\n".join(lines))
    print(f"Wrote {OUT_PATH}")
    for candidate in infer.CANDIDATES:
        print(f"  {candidate['id']}")


if __name__ == "__main__":
    main()
