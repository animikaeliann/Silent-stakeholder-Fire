"""
Semantic clustering validation pass. Purely additive and independent of
03_infer_gaps.py's deterministic keyword matching -- does NOT modify
output/gaps.json, output/rejected_candidates.jsonl, or re-run 03's main().
Imports 03's candidate definitions only to know which keyword clusters to
compare against.

Uses a local sentence-transformer (all-MiniLM-L6-v2, ~80MB, downloaded once
to the HF cache, no API key, no network calls at inference time) to embed
every normalized review, then:

  1. For each of the 3 shipped gaps, builds a semantic cluster by cosine
     similarity to the centroid of that gap's keyword-matched reviews, and
     compares its size/overlap against the keyword cluster.
  2. Runs unsupervised KMeans over all review embeddings to look for any
     large, cohesive cluster that isn't substantially covered by any of the
     3 shipped-gap filters or the 3 already-documented rejected-candidate
     filters -- i.e. something keyword matching could plausibly have missed
     entirely.

Usage: python scripts/06_semantic_clustering_check.py
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "output" / "semantic_validation.md"
MODEL_NAME = "all-MiniLM-L6-v2"

SEMANTIC_SIM_THRESHOLD = 0.45   # cosine similarity to a gap's keyword-cluster centroid
KMEANS_K = 30
MIN_NOVEL_CLUSTER_SIZE = 30      # below this, not worth flagging as a candidate
MAX_COVERAGE_TO_FLAG = 0.35      # if >35% of a cluster is already keyword-covered, not "novel"
MAX_MEAN_RATING_TO_FLAG = 2.5    # gaps are expressed as complaints; a praise-dominated cluster isn't one


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def embed_texts(model, texts, batch_size=64):
    return np.asarray(model.encode(texts, batch_size=batch_size, show_progress_bar=False,
                                    normalize_embeddings=True))


def cosine_to_centroid(embeddings, centroid):
    # embeddings and centroid are both L2-normalized, so dot product == cosine similarity
    return embeddings @ centroid


def known_filters():
    """All keyword predicates already accounted for: the 3 shipped gaps plus
    the 3 reconstructed rejected-candidate clusters from the sensitivity script."""
    infer = _load_module("03_infer_gaps.py")
    sensitivity = _load_module("05_rubric_sensitivity.py")
    filters = [(c["id"], c["review_filter"]) for c in infer.CANDIDATES]
    filters += [(c["id"], c["review_filter"]) for c in sensitivity.RECONSTRUCTED_REJECTED_CANDIDATES]
    return filters


def run(reviews, model, out_path, kmeans_k=KMEANS_K, min_novel_cluster_size=MIN_NOVEL_CLUSTER_SIZE,
        compare_to_shipped_gaps=True):
    """Core pipeline, parameterized so tests can run it on a small sample
    with a small kmeans_k instead of embedding the full 8k+ corpus."""
    infer = _load_module("03_infer_gaps.py")
    texts = [r["text"] for r in reviews]
    embeddings = embed_texts(model, texts)

    if compare_to_shipped_gaps:
        filters = known_filters()
    else:
        filters = []
    covered_ids_by_filter = {
        fid: {r["id"] for r in reviews if pred(r)} for fid, pred in filters
    }
    all_covered_ids = set().union(*covered_ids_by_filter.values()) if covered_ids_by_filter else set()

    lines = []
    lines.append("# Semantic clustering validation")
    lines.append("")
    lines.append(
        f"Independent check using local sentence embeddings ({MODEL_NAME}, no external API), "
        f"run against all {len(reviews)} normalized reviews. This does not replace or modify "
        "03_infer_gaps.py's keyword-based clustering -- it's a second opinion."
    )
    lines.append("")

    # --- Part 1: per-gap semantic cluster vs keyword cluster ---
    lines.append("## Part 1 — semantic cluster size vs keyword cluster size, per shipped gap")
    lines.append("")
    lines.append("| Gap | Keyword n | Semantic n (sim >= {:.2f}) | Overlap | Consistent? |".format(
        SEMANTIC_SIM_THRESHOLD))
    lines.append("|---|---|---|---|---|")

    part1_notes = []
    for cand in (infer.CANDIDATES if compare_to_shipped_gaps else []):
        keyword_ids = {r["id"] for r in reviews if cand["review_filter"](r)}
        idx = [i for i, r in enumerate(reviews) if r["id"] in keyword_ids]
        if not idx:
            continue
        centroid = embeddings[idx].mean(axis=0)
        centroid = centroid / np.linalg.norm(centroid)
        sims = cosine_to_centroid(embeddings, centroid)
        semantic_idx = np.where(sims >= SEMANTIC_SIM_THRESHOLD)[0]
        semantic_ids = {reviews[i]["id"] for i in semantic_idx}

        overlap = len(keyword_ids & semantic_ids)
        keyword_n = len(keyword_ids)
        semantic_n = len(semantic_ids)
        ratio = semantic_n / keyword_n if keyword_n else float("inf")
        consistent = 0.5 <= ratio <= 2.5  # semantic cluster within 2.5x of keyword cluster either way
        lines.append(
            f"| {cand['need'][:50]}… | {keyword_n} | {semantic_n} | {overlap} | "
            f"{'yes' if consistent else 'DIVERGES'} |"
        )
        part1_notes.append((cand, keyword_n, semantic_n, overlap, consistent, semantic_ids, keyword_ids))
    lines.append("")

    for cand, keyword_n, semantic_n, overlap, consistent, semantic_ids, keyword_ids in part1_notes:
        extra = semantic_ids - keyword_ids
        if extra and not consistent:
            sample_extra = list(extra)[:3]
            sample_texts = [r["text"][:140] for r in reviews if r["id"] in sample_extra]
            lines.append(f"**{cand['id']}**: semantic pass found {len(extra)} reviews above threshold "
                          f"that keyword matching missed. Sample: " + " | ".join(sample_texts))
            lines.append("")

    # --- Part 2: unsupervised discovery of anything keyword matching missed entirely ---
    lines.append("## Part 2 — unsupervised clustering for candidates keyword matching never targeted")
    lines.append("")
    print(f"Running KMeans (k={kmeans_k})...")
    from sklearn.cluster import KMeans
    km = KMeans(n_clusters=kmeans_k, random_state=42, n_init=10)
    labels = km.fit_predict(embeddings)

    novel_clusters = []
    for k in range(kmeans_k):
        member_idx = np.where(labels == k)[0]
        if len(member_idx) < min_novel_cluster_size:
            continue
        member_ids = {reviews[i]["id"] for i in member_idx}
        coverage = len(member_ids & all_covered_ids) / len(member_ids) if all_covered_ids else 0.0
        ratings = [reviews[i]["rating"] for i in member_idx if reviews[i]["rating"] is not None]
        mean_rating = sum(ratings) / len(ratings) if ratings else 5.0
        if coverage <= MAX_COVERAGE_TO_FLAG and mean_rating <= MAX_MEAN_RATING_TO_FLAG:
            novel_clusters.append((k, member_idx, member_ids, coverage, mean_rating))

    if not novel_clusters:
        lines.append(
            f"No cluster of size >= {min_novel_cluster_size} was found that is both "
            f"complaint-dominated (mean rating <= {MAX_MEAN_RATING_TO_FLAG}) and mostly uncovered "
            f"(<= {int(MAX_COVERAGE_TO_FLAG*100)}%) by an already-documented keyword cluster "
            "(the 3 shipped gaps + the 3 already-rejected candidates). Nothing new to report."
        )
    else:
        lines.append(
            f"{len(novel_clusters)} cluster(s) found that are large (>= {min_novel_cluster_size} "
            f"reviews), complaint-dominated (mean rating <= {MAX_MEAN_RATING_TO_FLAG}), and mostly "
            f"NOT covered by any existing keyword filter (<= {int(MAX_COVERAGE_TO_FLAG*100)}% "
            "overlap). Each is reported below with sample reviews for a human judgment call -- "
            "**none of these are added to gaps.json**; they have not been through roadmap "
            "cross-checking, confidence scoring, or falsification."
        )
        lines.append("")
        for k, member_idx, member_ids, coverage, mean_rating in sorted(novel_clusters, key=lambda x: -len(x[2])):
            sample_idx = list(member_idx)[:5]
            lines.append(f"### Cluster {k} — {len(member_ids)} reviews, mean rating {mean_rating:.1f}, "
                          f"{coverage*100:.0f}% already covered")
            lines.append("")
            lines.append("*Flagged by semantic pass, not yet validated through the falsification "
                          "pipeline -- your judgment call on whether this is a 4th gap candidate.*")
            lines.append("")
            for i in sample_idx:
                lines.append(f"- `{reviews[i]['id']}` (rating={reviews[i]['rating']}): "
                              f"{reviews[i]['text'][:160]}")
            lines.append("")

    out_path.write_text("\n".join(lines))
    print(f"Wrote {out_path}")
    print(f"Novel clusters flagged: {len(novel_clusters)}")
    return {"novel_clusters": len(novel_clusters), "part1": part1_notes}


def main():
    infer = _load_module("03_infer_gaps.py")
    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    print(f"Loading {MODEL_NAME}...")
    model = get_model()
    print(f"Embedding {len(reviews)} reviews...")
    run(reviews, model, OUT_PATH, kmeans_k=KMEANS_K, min_novel_cluster_size=MIN_NOVEL_CLUSTER_SIZE)


if __name__ == "__main__":
    main()
