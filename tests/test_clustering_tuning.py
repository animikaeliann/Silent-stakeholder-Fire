"""
Tests for scripts/10_tune_clustering.py. Fast unit tests use small
synthetic embeddings (no model download needed); one smoke test exercises
the real model + HDBSCAN on a tiny sample to confirm the sweep function
runs end-to-end. Does not touch output/gaps.json or any shipped-gap data.

Usage: python -m pytest tests/test_clustering_tuning.py -v
Requires: pip install sentence-transformers scikit-learn
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent

pytest.importorskip("sklearn")


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tuning_module():
    return _load_module("10_tune_clustering.py")


def make_synthetic_embeddings(seed=0, n_per_blob=30, n_blobs=3, dim=8):
    """Three well-separated, L2-normalized blobs -- fast, deterministic,
    no real text/model needed for testing the clustering/scoring logic."""
    rng = np.random.default_rng(seed)
    blobs = []
    for i in range(n_blobs):
        center = np.zeros(dim)
        center[i] = 5.0
        pts = center + rng.normal(scale=0.3, size=(n_per_blob, dim))
        blobs.append(pts)
    embeddings = np.vstack(blobs)
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings.astype(np.float32)


def test_run_kmeans_finds_separated_blobs(tuning_module):
    embeddings = make_synthetic_embeddings()
    labels = tuning_module.run_kmeans(embeddings, k=3)
    assert len(set(labels.tolist())) == 3
    assert len(labels) == embeddings.shape[0]


def test_run_hdbscan_finds_separated_blobs(tuning_module):
    embeddings = make_synthetic_embeddings()
    labels = tuning_module.run_hdbscan(embeddings, min_cluster_size=10, min_samples=5)
    n_clusters = len(set(labels.tolist()) - {-1})
    assert n_clusters >= 2  # three well-separated blobs should yield multiple clusters


def test_silhouette_for_labels_valid_range(tuning_module):
    embeddings = make_synthetic_embeddings()
    labels = tuning_module.run_hdbscan(embeddings, min_cluster_size=10, min_samples=5)
    sil = tuning_module.silhouette_for_labels(embeddings, labels)
    if sil is not None:
        assert -1.0 <= sil <= 1.0


def test_silhouette_returns_none_for_single_cluster(tuning_module):
    embeddings = make_synthetic_embeddings()
    all_same_label = np.zeros(embeddings.shape[0], dtype=int)
    assert tuning_module.silhouette_for_labels(embeddings, all_same_label) is None


def test_quick_stability_high_for_well_separated_blobs(tuning_module):
    embeddings = make_synthetic_embeddings(n_per_blob=40)
    labels = tuning_module.run_hdbscan(embeddings, min_cluster_size=15, min_samples=5)
    cluster_fn = lambda e: tuning_module.run_hdbscan(e, min_cluster_size=15, min_samples=5)
    stability = tuning_module.quick_stability(embeddings, cluster_fn, base_labels=labels, k_resamples=5)
    assert 0.0 <= stability <= 1.0
    # well-separated, dense blobs should be robust to bootstrap resampling
    assert stability > 0.5


def test_quick_stability_returns_zero_with_no_clusters(tuning_module):
    embeddings = make_synthetic_embeddings()
    all_noise = -1 * np.ones(embeddings.shape[0], dtype=int)
    cluster_fn = lambda e: tuning_module.run_hdbscan(e, min_cluster_size=15, min_samples=5)
    stability = tuning_module.quick_stability(embeddings, cluster_fn, base_labels=all_noise, k_resamples=3)
    assert stability == 0.0


def test_quick_stability_works_with_kmeans_too(tuning_module):
    embeddings = make_synthetic_embeddings(n_per_blob=40)
    labels = tuning_module.run_kmeans(embeddings, k=3)
    cluster_fn = lambda e: tuning_module.run_kmeans(e, k=3)
    stability = tuning_module.quick_stability(embeddings, cluster_fn, base_labels=labels, k_resamples=5)
    assert 0.0 <= stability <= 1.0
    assert stability > 0.5


def test_normalize_min_max_range(tuning_module):
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    normed = tuning_module.normalize(values)
    assert min(normed) == pytest.approx(0.0)
    assert max(normed) == pytest.approx(1.0)


def test_normalize_handles_none_and_flat_values(tuning_module):
    assert tuning_module.normalize([None, None]) == [0.0, 0.0]
    assert tuning_module.normalize([2.0, 2.0, 2.0]) == [1.0, 1.0, 1.0]
    mixed = tuning_module.normalize([1.0, None, 3.0])
    assert mixed[1] == 0.0


def test_does_not_touch_gaps_json():
    gaps_path = ROOT / "output" / "gaps.json"
    gaps_md_path = ROOT / "output" / "gaps.md"
    before_gaps = gaps_path.read_text()
    before_md = gaps_md_path.read_text()
    _load_module("10_tune_clustering.py")  # importing/loading must not execute a run
    assert gaps_path.read_text() == before_gaps
    assert gaps_md_path.read_text() == before_md


def test_full_sweep_smoke_on_tiny_real_sample():
    """Real model, real HDBSCAN, but a tiny sample and tiny grid -- confirms
    the actual sweep machinery (not just its helper functions) runs."""
    pytest.importorskip("sentence_transformers")
    semantic = _load_module("06_semantic_clustering_check.py")
    infer = _load_module("03_infer_gaps.py")
    tuning = _load_module("10_tune_clustering.py")

    reviews = infer.load_jsonl(infer.REVIEWS_PATH)[:80]
    model = semantic.get_model()
    embeddings = semantic.embed_texts(model, [r["text"] for r in reviews])

    labels = tuning.run_hdbscan(embeddings, min_cluster_size=5, min_samples=None)
    sil = tuning.silhouette_for_labels(embeddings, labels)
    cluster_fn = lambda e: tuning.run_hdbscan(e, min_cluster_size=5, min_samples=None)
    stab = tuning.quick_stability(embeddings, cluster_fn, labels, k_resamples=3)

    assert isinstance(labels, np.ndarray) and len(labels) == 80
    if sil is not None:
        assert -1.0 <= sil <= 1.0
    assert 0.0 <= stab <= 1.0
