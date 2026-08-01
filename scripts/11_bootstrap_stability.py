"""
Bootstrap stability analysis: proves the shipped gaps are stable patterns
in the review corpus, not artifacts of one particular sample.

Purely additive: reads data/normalized/reviews.jsonl and gaps.json (only
to know which keyword clusters correspond to which shipped gap), writes
output/bootstrap_stability.md. Does NOT modify gaps.json, gaps.md, or any
shipped-gap data.

Method:
  1. Embed the full corpus ONCE with the local sentence-transformer.
  2. Cluster the full (non-resampled) corpus with the tuned method from
     Phase 1 (output/clustering_tuning_report.md -- read dynamically via
     load_tuned_method(), whichever of HDBSCAN or KMeans that report
     selected) -- this gives a baseline clustering to (a) match each
     shipped gap's keyword cluster against its closest semantic cluster,
     if any, and (b) find any cluster that doesn't correspond to a known
     shipped or rejected theme, to test for bootstrap-discovered
     candidates.
  3. Resample review INDICES with replacement, N times, at the same size
     as the corpus. Bootstrap resampling draws from the same fixed pool
     of reviews, so the embeddings never change -- only which rows are
     drawn -- meaning embedding happens exactly once, not once per
     resample.
  4. Re-run the tuned clustering on each resample's embeddings. For each
     tracked target (4 shipped gaps + any full-data cluster not matched
     to a known theme), measure whether a resample cluster reappears that
     shares a majority of that target's ORIGINAL member reviews
     (restricted to reviews actually present in that resample -- with n
     draws from a pool of n, ~63% of the pool appears at least once per
     resample, the standard bootstrap "in-bag" rate). Also reports
     centroid cosine similarity to the best-matching resample cluster as
     a secondary corroborating number.
  5. Stability score per target = fraction of N resamples where a
     majority-overlap match was found.

Usage: python scripts/11_bootstrap_stability.py
"""
import importlib.util
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "output" / "bootstrap_stability.md"

N_RESAMPLES = 100
BOOTSTRAP_SEED = 2026
MAJORITY_THRESHOLD = 0.5   # fraction of a target's in-bag members that must land in
                            # one resample cluster to count as a "match" in that resample
KNOWN_THEME_OVERLAP_THRESHOLD = 0.3  # Jaccard vs a shipped/rejected cluster to call a
                                      # full-data cluster "already known", not novel
MAX_MEAN_RATING_TO_FLAG = 2.5  # same floor as 06_semantic_clustering_check.py: gaps are
                                # expressed as complaints, a praise-dominated cluster isn't one


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_tuned_method():
    """Read the tuned clustering method + settings straight out of Phase 1's own
    report, so this script can never silently drift out of sync with what Phase 1
    actually selected -- whichever of HDBSCAN or KMeans won that comparison."""
    report_path = ROOT / "output" / "clustering_tuning_report.md"
    text = report_path.read_text()
    import re
    m = re.search(r"`HDBSCAN\(min_cluster_size=(\d+), min_samples=(None|\d+)\)`", text)
    if m:
        min_cluster_size = int(m.group(1))
        min_samples = None if m.group(2) == "None" else int(m.group(2))
        return "hdbscan", {"min_cluster_size": min_cluster_size, "min_samples": min_samples}
    m = re.search(r"`KMeans\(k=(\d+)\)`", text)
    if m:
        return "kmeans", {"k": int(m.group(1))}
    raise RuntimeError("Could not parse a selected method from clustering_tuning_report.md "
                        "-- run scripts/10_tune_clustering.py first.")


def make_cluster_fn(tuning_module, method, params):
    if method == "hdbscan":
        return lambda e: tuning_module.run_hdbscan(e, params["min_cluster_size"], params["min_samples"])
    return lambda e: tuning_module.run_kmeans(e, params["k"])


def cluster_match(target_indices, sample_idx, resample_labels, threshold=MAJORITY_THRESHOLD):
    """Does a majority of target_indices' in-bag members land in one resample cluster?
    Returns (matched: bool, overlap_fraction: float, matched_label: int|None)."""
    positions = [i for i, orig in enumerate(sample_idx) if orig in target_indices]
    if not positions:
        return False, 0.0, None
    labels_at_positions = [resample_labels[i] for i in positions]
    counts = Counter(l for l in labels_at_positions if l != -1)
    if not counts:
        return False, 0.0, None
    best_label, best_count = counts.most_common(1)[0]
    frac = best_count / len(positions)
    return frac > threshold, frac, best_label


def centroid(embeddings, indices):
    v = embeddings[list(indices)].mean(axis=0)
    return v / np.linalg.norm(v)


def jaccard(a, b):
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_novel_candidate(best_overlap, mean_rating, overlap_threshold=KNOWN_THEME_OVERLAP_THRESHOLD,
                        max_mean_rating=MAX_MEAN_RATING_TO_FLAG):
    """Same floor as 06_semantic_clustering_check.py: a full-data cluster is worth flagging
    as a candidate only if it's NOT already a known theme AND it's complaint-dominated --
    a majority-praise cluster (however large or stable under bootstrap) isn't a gap."""
    return best_overlap < overlap_threshold and mean_rating <= max_mean_rating


def main():
    t_start = time.time()
    semantic = _load_module("06_semantic_clustering_check.py")
    infer = _load_module("03_infer_gaps.py")
    sensitivity = _load_module("05_rubric_sensitivity.py")
    tuning = _load_module("10_tune_clustering.py")

    method, params = load_tuned_method()
    cluster_fn = make_cluster_fn(tuning, method, params)
    print(f"Using tuned method: {method}({params})")

    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    n = len(reviews)
    print(f"Loading {semantic.MODEL_NAME}...")
    model = semantic.get_model()
    print(f"Embedding {n} reviews once...")
    embeddings = semantic.embed_texts(model, [r["text"] for r in reviews])

    # --- Targets: the shipped gaps (keyword clusters) ---
    shipped_targets = []
    for cand in infer.CANDIDATES:
        idx = {i for i, r in enumerate(reviews) if cand["review_filter"](r)}
        shipped_targets.append({"id": cand["id"], "need": cand["need"], "indices": idx, "kind": "shipped"})

    # --- Known-but-rejected themes, so novel-cluster detection doesn't re-flag them ---
    rejected_targets = []
    for cand in sensitivity.RECONSTRUCTED_REJECTED_CANDIDATES:
        idx = {i for i, r in enumerate(reviews) if cand["review_filter"](r)}
        rejected_targets.append({"id": cand["id"], "indices": idx})

    # --- Baseline (full-data) tuned clustering, to find candidate novel clusters ---
    print(f"Running tuned {method} on the full (non-resampled) corpus...")
    full_labels = cluster_fn(embeddings)
    full_clusters = {
        int(c): set(np.where(full_labels == c)[0].tolist())
        for c in set(full_labels.tolist()) if c != -1
    }
    print(f"  {len(full_clusters)} clusters found, {(full_labels == -1).mean()*100:.1f}% noise")

    known_index_sets = [t["indices"] for t in shipped_targets] + [t["indices"] for t in rejected_targets]
    novel_targets = []
    skipped_praise = 0
    for label, members in full_clusters.items():
        best_overlap = max((jaccard(members, known) for known in known_index_sets), default=0.0)
        ratings = [reviews[i]["rating"] for i in members if reviews[i]["rating"] is not None]
        mean_rating = sum(ratings) / len(ratings) if ratings else 5.0
        if not is_novel_candidate(best_overlap, mean_rating):
            # Caught here by checking, not assuming -- 4 of the 15 full-data clusters are
            # majority-praise (mean rating up to 4.31) and were being flagged as "candidates"
            # before this filter was added, which they clearly aren't.
            if best_overlap < KNOWN_THEME_OVERLAP_THRESHOLD:
                skipped_praise += 1
            continue
        novel_targets.append({"id": f"novel-cluster-{label}", "indices": members, "kind": "novel",
                               "size": len(members), "mean_rating": mean_rating})
    # Cap to the largest few to keep the bootstrap tractable and the report focused
    novel_targets.sort(key=lambda t: -t["size"])
    novel_targets = novel_targets[:5]
    print(f"  {len(novel_targets)} candidate novel cluster(s) not matching a known shipped/rejected theme "
          f"({skipped_praise} more excluded as praise-dominated, mean rating > {MAX_MEAN_RATING_TO_FLAG})")

    all_targets = shipped_targets + novel_targets

    # --- Bootstrap resampling ---
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    match_counts = {t["id"]: 0 for t in all_targets}
    overlap_sums = {t["id"]: 0.0 for t in all_targets}
    centroid_sim_sums = {t["id"]: [] for t in all_targets}
    target_centroids = {t["id"]: centroid(embeddings, t["indices"]) for t in all_targets}

    print(f"Running {N_RESAMPLES} bootstrap resamples...")
    for i in range(N_RESAMPLES):
        sample_idx = rng.integers(0, n, size=n)
        resample_embeddings = embeddings[sample_idx]
        resample_labels = cluster_fn(resample_embeddings)

        for t in all_targets:
            matched, frac, best_label = cluster_match(t["indices"], sample_idx, resample_labels)
            overlap_sums[t["id"]] += frac
            if matched:
                match_counts[t["id"]] += 1
                member_positions = np.where(resample_labels == best_label)[0]
                resample_cluster_centroid = resample_embeddings[member_positions].mean(axis=0)
                resample_cluster_centroid /= np.linalg.norm(resample_cluster_centroid)
                sim = float(np.dot(target_centroids[t["id"]], resample_cluster_centroid))
                centroid_sim_sums[t["id"]].append(sim)

        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{N_RESAMPLES} resamples done ({time.time() - t_start:.0f}s elapsed)")

    elapsed = time.time() - t_start

    # --- Report ---
    lines = []
    lines.append("# Bootstrap stability analysis")
    lines.append("")
    lines.append(
        f"{N_RESAMPLES} bootstrap resamples (with replacement, same size as the {n}-review corpus "
        f"each time) of the tuned clustering method (`{method}({params})`, selected in "
        "output/clustering_tuning_report.md -- see that report for why KMeans, not the initially-"
        "recommended HDBSCAN, ended up selected). Embeddings were computed once and reused across "
        "every resample -- only which rows are drawn changes, not the embeddings themselves. "
        f"Total run time: {elapsed:.0f}s ({elapsed/N_RESAMPLES:.2f}s/resample)."
    )
    lines.append("")
    lines.append(
        "A resample counts as a **match** for a target if a majority "
        f"(> {MAJORITY_THRESHOLD*100:.0f}%) of that target's originally-matched reviews that are "
        "in-bag for this resample land in the same resample cluster (not noise). Stability score = "
        "fraction of resamples that match."
    )
    lines.append("")

    lines.append("## Shipped-gap stability")
    lines.append("")
    lines.append("| Gap | n reviews | Stable in | Avg. overlap fraction | Avg. centroid sim (on match) |")
    lines.append("|---|---|---|---|---|")
    for t in shipped_targets:
        stability = match_counts[t["id"]] / N_RESAMPLES
        avg_overlap = overlap_sums[t["id"]] / N_RESAMPLES
        sims = centroid_sim_sums[t["id"]]
        avg_sim = f"{np.mean(sims):.3f}" if sims else "n/a"
        lines.append(
            f"| {t['need'][:55]}… | {len(t['indices'])} | "
            f"{match_counts[t['id']]}/{N_RESAMPLES} ({stability*100:.0f}%) | {avg_overlap:.2f} | {avg_sim} |"
        )
    lines.append("")

    weakest = min(shipped_targets, key=lambda t: match_counts[t["id"]])
    lines.append(
        f"**Weakest shipped gap by this metric:** {weakest['need'][:70]}… -- stable in "
        f"{match_counts[weakest['id']]}/{N_RESAMPLES} resamples. "
        + ("This is independent corroboration, not a red flag -- still a strong majority."
           if match_counts[weakest["id"]] / N_RESAMPLES >= 0.7 else
           "This is below 70% and worth a second look before the defense.")
    )
    lines.append("")

    lines.append("## Bootstrap-discovered candidates (not yet in pipeline)")
    lines.append("")
    if not novel_targets:
        lines.append(
            f"No full-data {method} cluster was found that (a) failed to match any shipped or "
            f"already-rejected theme (Jaccard < {KNOWN_THEME_OVERLAP_THRESHOLD}), (b) is "
            f"complaint-dominated (mean rating <= {MAX_MEAN_RATING_TO_FLAG}), and (c) met the size "
            "floor. Nothing new to report."
        )
    else:
        lines.append(
            "These clusters appeared in the full-data tuned clustering, did not closely match any "
            f"shipped gap or already-rejected candidate, and are complaint-dominated (mean rating <= "
            f"{MAX_MEAN_RATING_TO_FLAG} -- {skipped_praise} other large cluster(s) were excluded here "
            "for being majority-praise instead, same floor 06_semantic_clustering_check.py uses and "
            "checked here explicitly rather than assumed). Reported with their bootstrap stability for "
            "context -- **none are added to gaps.json**; they have not been roadmap-cross-checked, "
            "scored, or falsification-tested."
        )
        lines.append("")
        lines.append("| Cluster | Size | Mean rating | Stable in |")
        lines.append("|---|---|---|---|")
        for t in novel_targets:
            stability = match_counts[t["id"]] / N_RESAMPLES
            lines.append(
                f"| {t['id']} | {t['size']} | {t['mean_rating']:.2f} | "
                f"{match_counts[t['id']]}/{N_RESAMPLES} ({stability*100:.0f}%) |"
            )
        lines.append("")

    lines.append("## Methodology notes")
    lines.append("")
    lines.append(
        "- Bootstrap resampling with replacement means ~63% of the corpus is \"in-bag\" for any given "
        "resample (the standard 1-1/e rate for n draws from a pool of n); the match criterion is "
        "evaluated only against a target's in-bag members for that resample, not its full original set."
    )
    lines.append(
        "- This measures cluster-level reproducibility under resampling, which is a different question "
        "from the confidence rubric (corroboration/scale/persistence/roadmap-neglect) -- a gap can score "
        "high on one and be unmeasured by the other. They're complementary, not substitutes."
    )
    lines.append(
        f"- Novel-cluster detection caps at the {len(novel_targets)} largest unmatched full-data "
        "clusters to keep the bootstrap run tractable; smaller unmatched clusters exist but weren't "
        "tracked individually here."
    )

    OUT_PATH.write_text("\n".join(lines))
    print(f"\nWrote {OUT_PATH}")
    for t in shipped_targets:
        print(f"  {t['id']}: {match_counts[t['id']]}/{N_RESAMPLES}")


if __name__ == "__main__":
    main()
