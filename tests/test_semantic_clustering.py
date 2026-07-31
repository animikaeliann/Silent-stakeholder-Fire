"""
Smoke test for scripts/06_semantic_clustering_check.py. Runs the real
pipeline (real model, real embeddings) but on a small sample with a small
kmeans_k, so it stays fast and doesn't touch output/semantic_validation.md
(the real run's output) or output/gaps.json.

Usage: python -m pytest tests/test_semantic_clustering.py -v
Requires: pip install sentence-transformers scikit-learn
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

pytest.importorskip("sentence_transformers")
pytest.importorskip("sklearn")


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def semantic_module():
    return _load_module("06_semantic_clustering_check.py")


@pytest.fixture(scope="module")
def model(semantic_module):
    return semantic_module.get_model()


@pytest.fixture(scope="module")
def sample_reviews(semantic_module):
    infer = _load_module("03_infer_gaps.py")
    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    return reviews[:60]


def test_embed_texts_returns_normalized_vectors(semantic_module, model, sample_reviews):
    import numpy as np
    texts = [r["text"] for r in sample_reviews[:10]]
    embeddings = semantic_module.embed_texts(model, texts)
    assert embeddings.shape[0] == 10
    norms = np.linalg.norm(embeddings, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-3)


def test_cosine_to_centroid_range(semantic_module, model, sample_reviews):
    import numpy as np
    texts = [r["text"] for r in sample_reviews[:10]]
    embeddings = semantic_module.embed_texts(model, texts)
    centroid = embeddings[:3].mean(axis=0)
    centroid = centroid / np.linalg.norm(centroid)
    sims = semantic_module.cosine_to_centroid(embeddings, centroid)
    assert sims.shape == (10,)
    assert (sims >= -1.0001).all() and (sims <= 1.0001).all()


def test_run_on_small_sample_produces_valid_report(tmp_path, semantic_module, model, sample_reviews):
    out_path = tmp_path / "semantic_validation_sample.md"
    result = semantic_module.run(
        sample_reviews, model, out_path,
        kmeans_k=3, min_novel_cluster_size=5, compare_to_shipped_gaps=False,
    )
    assert out_path.exists()
    text = out_path.read_text()
    assert "Semantic clustering validation" in text
    assert "Part 2" in text
    assert isinstance(result["novel_clusters"], int)
    assert result["novel_clusters"] >= 0


def test_run_does_not_touch_real_output_files(tmp_path, semantic_module, model, sample_reviews):
    gaps_path = ROOT / "output" / "gaps.json"
    real_semantic_path = ROOT / "output" / "semantic_validation.md"
    before_gaps = gaps_path.read_text()
    before_semantic = real_semantic_path.read_text() if real_semantic_path.exists() else None

    out_path = tmp_path / "sample_out.md"
    semantic_module.run(sample_reviews, model, out_path, kmeans_k=3, min_novel_cluster_size=5,
                         compare_to_shipped_gaps=False)

    assert gaps_path.read_text() == before_gaps
    if before_semantic is not None:
        assert real_semantic_path.read_text() == before_semantic
