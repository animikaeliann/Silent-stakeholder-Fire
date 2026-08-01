"""
Tests for scripts/13_semantic_falsification.py, including the two known
regression cases the module docstring calibrates its threshold against.
Does not touch output/gaps.json or any shipped-gap data.

Usage: python -m pytest tests/test_semantic_falsification.py -v
Requires: pip install sentence-transformers
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent

pytest.importorskip("sentence_transformers")


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def falsification_module():
    return _load_module("13_semantic_falsification.py")


@pytest.fixture(scope="module")
def model(falsification_module):
    semantic = _load_module("06_semantic_clustering_check.py")
    return semantic.get_model()


@pytest.fixture(scope="module")
def exemplar_embeddings(falsification_module, model):
    semantic = _load_module("06_semantic_clustering_check.py")
    return semantic.embed_texts(model, falsification_module.RESOLUTION_EXEMPLARS)


def test_max_similarity_shape_and_range(falsification_module, model, exemplar_embeddings):
    semantic = _load_module("06_semantic_clustering_check.py")
    texts = ["great app", "terrible bug", "fixed now, thanks"]
    embeddings = semantic.embed_texts(model, texts)
    scores = falsification_module.max_similarity_to_exemplars(embeddings, exemplar_embeddings)
    assert scores.shape == (3,)
    assert ((-1.0001 <= scores) & (scores <= 1.0001)).all()


def test_known_resolution_review_06529_clears_threshold(falsification_module, model, exemplar_embeddings):
    """review-play-06529: 'Fixed the issue I had with videos crashing the app.
    Works great now!' -- the clearer of the two known regression cases."""
    semantic = _load_module("06_semantic_clustering_check.py")
    infer = _load_module("03_infer_gaps.py")
    reviews = {r["id"]: r for r in infer.load_jsonl(infer.REVIEWS_PATH)}
    text = reviews["review-play-06529"]["text"]
    embedding = semantic.embed_texts(model, [text])
    score = falsification_module.max_similarity_to_exemplars(embedding, exemplar_embeddings)[0]
    assert score >= falsification_module.SIMILARITY_THRESHOLD


def test_known_resolution_review_06841_clears_threshold(falsification_module, model, exemplar_embeddings):
    """review-play-06841: 'Thank you for finally fixing the video crashing...'
    -- the borderline case that drove the threshold down to 0.30."""
    semantic = _load_module("06_semantic_clustering_check.py")
    infer = _load_module("03_infer_gaps.py")
    reviews = {r["id"]: r for r in infer.load_jsonl(infer.REVIEWS_PATH)}
    text = reviews["review-play-06841"]["text"]
    embedding = semantic.embed_texts(model, [text])
    score = falsification_module.max_similarity_to_exemplars(embedding, exemplar_embeddings)[0]
    assert score >= falsification_module.SIMILARITY_THRESHOLD


def test_unrelated_review_does_not_clear_threshold(falsification_module, model, exemplar_embeddings):
    semantic = _load_module("06_semantic_clustering_check.py")
    text = "Rating the app, not bsky as a whole. Works well, clear and intuitive."
    embedding = semantic.embed_texts(model, [text])
    score = falsification_module.max_similarity_to_exemplars(embedding, exemplar_embeddings)[0]
    assert score < falsification_module.SIMILARITY_THRESHOLD


def test_flag_resolution_signals_returns_sorted_flagged_list(falsification_module, model, exemplar_embeddings):
    semantic = _load_module("06_semantic_clustering_check.py")
    reviews = [
        {"id": "a", "text": "Fixed! Thanks for the quick fix, works great now."},
        {"id": "b", "text": "This app is a complete joke, unusable garbage."},
        {"id": "c", "text": "They finally sorted this out, no longer an issue."},
    ]
    embeddings = semantic.embed_texts(model, [r["text"] for r in reviews])
    flagged, scores = falsification_module.flag_resolution_signals(reviews, embeddings, exemplar_embeddings)
    assert len(scores) == 3
    flagged_ids = {f["id"] for f in flagged}
    assert "b" not in flagged_ids
    # flagged list must be sorted descending by score
    assert all(flagged[i]["score"] >= flagged[i + 1]["score"] for i in range(len(flagged) - 1))


def test_does_not_touch_gaps_json():
    gaps_path = ROOT / "output" / "gaps.json"
    before = gaps_path.read_text()
    assert gaps_path.read_text() == before
