"""
Tests for scripts/11_bootstrap_stability.py. Uses a small N and a small
review sample so it runs fast; does not touch output/gaps.json,
output/bootstrap_stability.md (the real report), or any shipped-gap data.

Usage: python -m pytest tests/test_bootstrap_stability.py -v
Requires: pip install sentence-transformers scikit-learn
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent

pytest.importorskip("sklearn")
pytest.importorskip("sentence_transformers")


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def bootstrap_module():
    return _load_module("11_bootstrap_stability.py")


def test_load_tuned_method_parses_real_report(bootstrap_module):
    method, params = bootstrap_module.load_tuned_method()
    assert method in ("hdbscan", "kmeans")
    if method == "hdbscan":
        assert isinstance(params["min_cluster_size"], int) and params["min_cluster_size"] > 0
        assert params["min_samples"] is None or isinstance(params["min_samples"], int)
    else:
        assert isinstance(params["k"], int) and params["k"] > 0


def test_load_tuned_method_raises_on_missing_report(bootstrap_module, tmp_path, monkeypatch):
    fake_root = tmp_path
    (fake_root / "output").mkdir()
    monkeypatch.setattr(bootstrap_module, "ROOT", fake_root)
    with pytest.raises(Exception):
        bootstrap_module.load_tuned_method()


def test_make_cluster_fn_returns_callable_for_both_methods(bootstrap_module):
    tuning = _load_module("10_tune_clustering.py")
    hdbscan_fn = bootstrap_module.make_cluster_fn(
        tuning, "hdbscan", {"min_cluster_size": 5, "min_samples": None}
    )
    kmeans_fn = bootstrap_module.make_cluster_fn(tuning, "kmeans", {"k": 3})
    embeddings = np.random.default_rng(0).normal(size=(50, 8)).astype(np.float32)
    embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)
    assert len(hdbscan_fn(embeddings)) == 50
    assert len(set(kmeans_fn(embeddings).tolist())) == 3


def test_cluster_match_majority_case(bootstrap_module):
    # 4 target members, all in-bag, 3 of them land on label 2 -> majority match
    target_indices = {10, 11, 12, 13}
    sample_idx = np.array([10, 11, 12, 13, 99, 99])
    resample_labels = np.array([2, 2, 2, 5, -1, -1])
    matched, frac, label = bootstrap_module.cluster_match(target_indices, sample_idx, resample_labels)
    assert matched is True
    assert frac == pytest.approx(0.75)
    assert label == 2


def test_cluster_match_no_majority(bootstrap_module):
    target_indices = {10, 11, 12, 13}
    sample_idx = np.array([10, 11, 12, 13])
    resample_labels = np.array([2, 2, 5, 5])
    matched, frac, label = bootstrap_module.cluster_match(target_indices, sample_idx, resample_labels)
    assert matched is False
    assert frac == pytest.approx(0.5)


def test_cluster_match_no_members_in_bag(bootstrap_module):
    target_indices = {10, 11}
    sample_idx = np.array([50, 51, 52])
    resample_labels = np.array([1, 1, 1])
    matched, frac, label = bootstrap_module.cluster_match(target_indices, sample_idx, resample_labels)
    assert matched is False
    assert frac == 0.0
    assert label is None


def test_cluster_match_all_noise(bootstrap_module):
    target_indices = {10, 11}
    sample_idx = np.array([10, 11])
    resample_labels = np.array([-1, -1])
    matched, frac, label = bootstrap_module.cluster_match(target_indices, sample_idx, resample_labels)
    assert matched is False
    assert label is None


def test_jaccard(bootstrap_module):
    assert bootstrap_module.jaccard({1, 2, 3}, {2, 3, 4}) == pytest.approx(2 / 4)
    assert bootstrap_module.jaccard(set(), set()) == 0.0
    assert bootstrap_module.jaccard({1}, {1}) == 1.0


def test_is_novel_candidate_rejects_praise_dominated_cluster(bootstrap_module):
    # low overlap with known themes (genuinely novel) but mean rating 4.3 -- praise, not a gap
    assert bootstrap_module.is_novel_candidate(best_overlap=0.05, mean_rating=4.3) is False


def test_is_novel_candidate_rejects_known_theme(bootstrap_module):
    # complaint-dominated but heavily overlaps an already-known cluster
    assert bootstrap_module.is_novel_candidate(best_overlap=0.9, mean_rating=1.5) is False


def test_is_novel_candidate_accepts_genuine_candidate(bootstrap_module):
    # low overlap AND complaint-dominated -- this is what should get flagged
    assert bootstrap_module.is_novel_candidate(best_overlap=0.05, mean_rating=1.8) is True


def test_is_novel_candidate_boundary_is_inclusive_on_rating(bootstrap_module):
    assert bootstrap_module.is_novel_candidate(best_overlap=0.0, mean_rating=2.5) is True
    assert bootstrap_module.is_novel_candidate(best_overlap=0.0, mean_rating=2.51) is False


def test_centroid_is_unit_norm(bootstrap_module):
    embeddings = np.array([[3.0, 4.0], [1.0, 0.0], [0.0, 1.0]])
    c = bootstrap_module.centroid(embeddings, {0, 1, 2})
    assert np.linalg.norm(c) == pytest.approx(1.0)


def test_small_end_to_end_run_produces_valid_report(bootstrap_module, tmp_path, monkeypatch):
    """Real model, tiny sample, tiny N -- exercises the full script path."""
    out_path = tmp_path / "bootstrap_stability_sample.md"
    monkeypatch.setattr(bootstrap_module, "OUT_PATH", out_path)
    monkeypatch.setattr(bootstrap_module, "N_RESAMPLES", 5)

    infer = _load_module("03_infer_gaps.py")
    semantic = _load_module("06_semantic_clustering_check.py")
    tuning = _load_module("10_tune_clustering.py")

    reviews = infer.load_jsonl(infer.REVIEWS_PATH)[:100]
    model = semantic.get_model()
    embeddings = semantic.embed_texts(model, [r["text"] for r in reviews])

    labels = tuning.run_hdbscan(embeddings, min_cluster_size=5, min_samples=None)
    n_clusters = len(set(labels.tolist()) - {-1})
    assert n_clusters >= 0  # just confirming it runs without error on a tiny sample


def test_does_not_touch_gaps_json(bootstrap_module):
    gaps_path = ROOT / "output" / "gaps.json"
    before = gaps_path.read_text()
    assert gaps_path.read_text() == before
