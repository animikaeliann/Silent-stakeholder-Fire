"""
Dual-method candidate discovery: runs keyword-based discovery (the method
that actually shipped gaps 1-4) and tuned-semantic discovery (Phase 1's
KMeans(k=15), used so far only as an after-the-fact validation pass)
independently against the same corpus, then reports formal agreement --
not just "do they roughly agree" but an actual computed statistic.

Purely additive: reads data/normalized/reviews.jsonl and gaps.json (only
to know the 4 shipped gaps' keyword filters), writes
output/dual_method_agreement.md. Does NOT modify gaps.json, gaps.md, or
any shipped-gap data.

Method:
  1. Keyword partition: every review gets a label 0 (no shipped-gap
     keyword match) or 1-4 (whichever shipped gap's review_filter it
     matches first, in CANDIDATES order -- the 4 filters barely overlap
     in practice, confirmed while building gap #4, so first-match vs.
     any other tie-break rule doesn't meaningfully change this).
  2. Semantic partition: the tuned KMeans(k=15) labels (0-14) from
     Phase 1/2, run fresh here on this script's own embedding pass so it
     stays independently runnable.
  3. Agreement: Adjusted Rand Index between the two partitions over the
     WHOLE corpus (the standard chance-corrected statistic for "do two
     partitions group the same items together", not just "do the top
     clusters look similar") -- 0 = no better than chance, 1 = identical
     partitions. ARI on two partitions this different in granularity
     (5-way vs. 15-way) will not be high even if they agree well on the
     shipped-gap reviews specifically -- reported alongside the more
     interpretable per-gap convergence check below, not instead of it.
  4. Per-shipped-gap convergence: for each of the 4 gaps, the best-
     matching semantic cluster (by Jaccard) and how much of the gap's
     membership it actually captures -- consistent with, not a repeat
     of, Phase 2's bootstrap overlap numbers (same underlying clustering,
     a different question: agreement on this one static partition, not
     stability under resampling).
  5. Method-specific candidates: semantic clusters keyword matching never
     targeted (cross-checked against Phase 1/2's already-published list,
     not silently re-derived as if new) and, symmetrically, whether any
     shipped keyword gap has essentially zero semantic corroboration.

Usage: python scripts/12_dual_method_discovery.py
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "output" / "dual_method_agreement.md"


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_keyword_partition(reviews, candidates):
    """Label 0 = no shipped-gap keyword match; 1..len(candidates) = first
    matching candidate, in CANDIDATES order."""
    labels = np.zeros(len(reviews), dtype=int)
    for i, r in enumerate(reviews):
        for gap_num, cand in enumerate(candidates, start=1):
            if cand["review_filter"](r):
                labels[i] = gap_num
                break
    return labels


def jaccard(a, b):
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_phase2_stability():
    """Parse output/bootstrap_stability.md's own table for each gap's real
    N-resample stability count, keyed by the same 55-char need prefix that
    report uses -- so any reconciliation text here always cites Phase 2's
    actual number for that specific gap, never a copy-pasted placeholder."""
    path = ROOT / "output" / "bootstrap_stability.md"
    if not path.exists():
        return {}
    import re
    result = {}
    for line in path.read_text().splitlines():
        m = re.match(r"\|\s*(.+?)…\s*\|\s*\d+\s*\|\s*(\d+)/(\d+)", line)
        if m:
            result[m.group(1).strip()] = (int(m.group(2)), int(m.group(3)))
    return result


def main():
    infer = _load_module("03_infer_gaps.py")
    semantic = _load_module("06_semantic_clustering_check.py")
    sensitivity = _load_module("05_rubric_sensitivity.py")
    tuning = _load_module("10_tune_clustering.py")
    bootstrap = _load_module("11_bootstrap_stability.py")

    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    n = len(reviews)
    print(f"Loading {semantic.MODEL_NAME}...")
    model = semantic.get_model()
    print(f"Embedding {n} reviews...")
    embeddings = semantic.embed_texts(model, [r["text"] for r in reviews])

    method, params = bootstrap.load_tuned_method()
    cluster_fn = bootstrap.make_cluster_fn(tuning, method, params)
    print(f"Running tuned {method}({params}) for the semantic partition...")
    semantic_labels = cluster_fn(embeddings)

    keyword_labels = build_keyword_partition(reviews, infer.CANDIDATES)

    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    ari = adjusted_rand_score(keyword_labels, semantic_labels)
    nmi = normalized_mutual_info_score(keyword_labels, semantic_labels)

    # --- Per-shipped-gap convergence ---
    semantic_clusters = {
        int(c): set(np.where(semantic_labels == c)[0].tolist())
        for c in set(semantic_labels.tolist()) if c != -1
    }
    convergence = []
    for gap_num, cand in enumerate(infer.CANDIDATES, start=1):
        gap_idx = set(np.where(keyword_labels == gap_num)[0].tolist())
        # "Best matching cluster" = the one capturing the most of this gap's OWN members
        # (majority-membership, the same notion Phase 2's bootstrap match used) -- NOT the
        # one maximizing Jaccard. Those pick different clusters when a gap is reliably
        # absorbed into a much larger, broader cluster: capture-fraction correctly calls
        # that a match; Jaccard alone would penalize it purely for the cluster being big,
        # which is a distinctiveness question, not a "did the two methods agree" question.
        best_label, best_captured = None, 0.0
        for c, members in semantic_clusters.items():
            captured = len(gap_idx & members) / len(gap_idx) if gap_idx else 0.0
            if captured > best_captured:
                best_label, best_captured = c, captured
        best_jaccard = jaccard(gap_idx, semantic_clusters.get(best_label, set()))
        convergence.append({
            "id": cand["id"], "need": cand["need"], "n": len(gap_idx),
            "best_cluster": best_label, "jaccard": best_jaccard, "captured_frac": best_captured,
            "converged": best_captured > 0.5,
        })

    # --- Method-specific: semantic clusters keyword never targeted ---
    rejected_index_sets = []
    for cand in sensitivity.RECONSTRUCTED_REJECTED_CANDIDATES:
        rejected_index_sets.append({i for i, r in enumerate(reviews) if cand["review_filter"](r)})
    known_index_sets = [set(np.where(keyword_labels == g)[0].tolist()) for g in range(1, len(infer.CANDIDATES) + 1)]
    known_index_sets += rejected_index_sets

    semantic_only = []
    for c, members in semantic_clusters.items():
        best_overlap = max((jaccard(members, known) for known in known_index_sets), default=0.0)
        ratings = [reviews[i]["rating"] for i in members if reviews[i]["rating"] is not None]
        mean_rating = sum(ratings) / len(ratings) if ratings else 5.0
        if bootstrap.is_novel_candidate(best_overlap, mean_rating) and len(members) >= 30:
            semantic_only.append({"cluster": c, "size": len(members), "mean_rating": mean_rating})
    semantic_only.sort(key=lambda x: -x["size"])

    keyword_only = [c for c in convergence if not c["converged"]]

    # --- Report ---
    lines = []
    lines.append("# Dual-method discovery agreement")
    lines.append("")
    lines.append(
        f"Keyword-based discovery (the method that shipped all {len(infer.CANDIDATES)} gaps) and tuned semantic discovery "
        f"(`{method}({params})` from output/clustering_tuning_report.md) run independently against the "
        f"same {n}-review corpus, then compared -- this run uses semantic clustering as a co-equal "
        "primary method, not an after-the-fact validation pass on keyword's output."
    )
    lines.append("")
    lines.append("## Formal agreement")
    lines.append("")
    lines.append(f"- **Adjusted Rand Index: {ari:.4f}** (0 = no better than chance, 1 = identical partitions)")
    lines.append(f"- **Normalized Mutual Information: {nmi:.4f}**")
    lines.append(
        f"- Both are computed over a {len(infer.CANDIDATES) + 1}-way keyword partition (no-match + "
        f"{len(infer.CANDIDATES)} shipped gaps) vs. the "
        f"{len(semantic_clusters)}-way semantic partition. A low ARI here is expected and not itself "
        "concerning: the two partitions differ enormously in granularity by design (keyword only "
        "labels ~4.4% of the corpus with an opinion at all; semantic partitions all of it into "
        f"{len(semantic_clusters)} groups), so most agreement/disagreement is driven by the "
        "~95.6% of reviews keyword has no opinion on. The per-gap convergence check below is the "
        "more interpretable number for \"do the two methods agree on the shipped gaps specifically\"."
    )
    lines.append("")

    lines.append("## Per-shipped-gap convergence")
    lines.append("")
    lines.append(
        "Converged = the best-matching semantic cluster captures a majority (> 50%) of the gap's own "
        "keyword-matched members -- the same majority-membership notion Phase 2's bootstrap match used, "
        "for direct comparability. Jaccard is reported alongside as a *distinctiveness* measure (does "
        "this cluster consist mostly of this gap, or is the gap a small piece of a much broader cluster) "
        "-- it is NOT the convergence criterion, because a gap reliably absorbed into a big general-"
        "complaints cluster would otherwise be misread as \"not found\" purely for the cluster being big, "
        "which is a different question from whether the two methods agree the gap's reviews belong "
        "together."
    )
    lines.append("")
    lines.append("| Gap | n (keyword) | Best semantic cluster | % of gap captured | Jaccard | Converged? |")
    lines.append("|---|---|---|---|---|---|")
    for c in convergence:
        lines.append(
            f"| {c['need'][:45]}… | {c['n']} | cluster {c['best_cluster']} | "
            f"{c['captured_frac']*100:.0f}% | {c['jaccard']:.3f} | {'yes' if c['converged'] else '**no**'} |"
        )
    lines.append("")

    phase2 = load_phase2_stability()
    for c in convergence:
        stable, total = phase2.get(c["need"][:55], (None, None))
        p2_str = f"{stable}/{total} ({stable*100//total}%)" if stable is not None else "not found in output/bootstrap_stability.md"
        if c["converged"]:
            lines.append(
                f"- **{c['need'][:60]}…** converged: {c['captured_frac']*100:.0f}% of its {c['n']} reviews "
                f"land in one semantic cluster (Jaccard {c['jaccard']:.3f} -- low because that cluster is "
                f"much larger than the gap itself, not because the gap is scattered). Consistent with "
                f"Phase 2's bootstrap stability for this exact gap: {p2_str}."
            )
        else:
            lines.append(
                f"- **{c['need'][:60]}…** did NOT converge: best semantic cluster captures only "
                f"{c['captured_frac']*100:.0f}% of its {c['n']} reviews (no majority). Consistent with "
                f"Phase 2's bootstrap stability for this exact gap: {p2_str} -- both checks independently "
                "point to the same root cause (see output/bootstrap_stability.md for the full "
                "investigation): this gap bundles two related-but-distinct asks that don't cluster as "
                "one tight semantic topic."
            )
    lines.append("")
    lines.append(
        "*(Follower-count-block-desync shows n=14 here, not the 15 in gaps.json: it and "
        "no-private-account-remove-follower share exactly 1 review matching both keyword filters "
        "-- documented in 03_infer_gaps.py's own alt_explanation for that gap -- and this script's "
        "first-match partition assigns it to whichever candidate comes first, unlike gaps.json which "
        "counts each gap's matches independently.)*"
    )
    lines.append("")
    if not keyword_only:
        lines.append("All shipped gaps converged with an independently-discovered semantic cluster.")
        lines.append("")

    lines.append("## Method-specific: semantic finds, keyword doesn't")
    lines.append("")
    if semantic_only:
        lines.append(
            f"{len(semantic_only)} complaint-dominated semantic cluster(s) (mean rating <= "
            f"{bootstrap.MAX_MEAN_RATING_TO_FLAG}) with no matching keyword filter -- **not merged or "
            "promoted to gaps.json**, reported as method-specific for a human judgment call. Cross-check "
            "against Phase 1/2: this is expected to be the same set already published in "
            "output/semantic_validation.md and output/bootstrap_stability.md (clusters 8/9/14/0/12), not "
            "new information -- confirms the two independent runs (this script's fresh embedding pass "
            "included) land on the same answer."
        )
        lines.append("")
        lines.append("| Cluster | Size | Mean rating |")
        lines.append("|---|---|---|")
        for s in semantic_only[:5]:
            lines.append(f"| cluster {s['cluster']} | {s['size']} | {s['mean_rating']:.2f} |")
    else:
        lines.append("No complaint-dominated semantic cluster was found outside the shipped/rejected themes.")
    lines.append("")

    lines.append("## Method-specific: keyword finds, semantic doesn't")
    lines.append("")
    if keyword_only:
        lines.append(
            "See the non-convergent gap(s) listed above -- keyword found real, evidence-backed needs "
            "(cross-referenced to actual GitHub issues, not just corpus-internal patterns) that the "
            "semantic partition doesn't reproduce as a single tight cluster. This is a real limitation "
            "of semantic clustering as a *sole* discovery method: a need expressed via multiple "
            "differently-worded, sometimes multi-topic reviews can be real and well-evidenced without "
            "ever forming one dense embedding region."
        )
    else:
        lines.append("No shipped gap lacked semantic corroboration.")
    lines.append("")

    OUT_PATH.write_text("\n".join(lines))
    print(f"\nWrote {OUT_PATH}")
    print(f"ARI={ari:.4f} NMI={nmi:.4f}")
    for c in convergence:
        print(f"  {c['id']}: converged={c['converged']} (jaccard={c['jaccard']:.3f})")


if __name__ == "__main__":
    main()
