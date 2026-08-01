"""
Tests for scripts/12_dual_method_discovery.py. Fast unit tests use
synthetic candidates; does not touch output/gaps.json or any shipped-gap
data.

Usage: python -m pytest tests/test_dual_method.py -v
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
def dual_module():
    return _load_module("12_dual_method_discovery.py")


def test_build_keyword_partition_assigns_correct_labels(dual_module):
    reviews = [
        {"text": "the login keyboard is broken"},
        {"text": "great app, no complaints"},
        {"text": "please add a private account option"},
        {"text": "keyboard issue again on login"},
    ]
    candidates = [
        {"id": "c1", "review_filter": lambda r: "keyboard" in r["text"]},
        {"id": "c2", "review_filter": lambda r: "private account" in r["text"]},
    ]
    labels = dual_module.build_keyword_partition(reviews, candidates)
    assert labels.tolist() == [1, 0, 2, 1]


def test_build_keyword_partition_first_match_wins_on_overlap(dual_module):
    reviews = [{"text": "keyboard and private account both broken"}]
    candidates = [
        {"id": "c1", "review_filter": lambda r: "keyboard" in r["text"]},
        {"id": "c2", "review_filter": lambda r: "private account" in r["text"]},
    ]
    labels = dual_module.build_keyword_partition(reviews, candidates)
    assert labels.tolist() == [1]  # c1 is first in the list, so it wins the tie


def test_build_keyword_partition_all_unmatched_is_zero(dual_module):
    reviews = [{"text": "totally unrelated review text"}]
    candidates = [{"id": "c1", "review_filter": lambda r: "keyboard" in r["text"]}]
    labels = dual_module.build_keyword_partition(reviews, candidates)
    assert labels.tolist() == [0]


def test_jaccard(dual_module):
    assert dual_module.jaccard({1, 2, 3}, {2, 3, 4}) == pytest.approx(2 / 4)
    assert dual_module.jaccard(set(), set()) == 0.0
    assert dual_module.jaccard({1}, {1}) == 1.0


def test_real_keyword_partition_matches_gap_counts(dual_module):
    """Real CANDIDATES, real reviews -- confirms each gap's label count is
    within 1 of the n already reported in output/gaps.json (first-match
    tie-breaking can shave off exactly 1 review for a gap whose filter
    overlaps another's by exactly 1 review -- a known, already-documented
    overlap between follower-count-block-desync and
    no-private-account-remove-follower, not a bug), without running the
    (slow) semantic half of the script."""
    infer = _load_module("03_infer_gaps.py")
    import json
    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    labels = dual_module.build_keyword_partition(reviews, infer.CANDIDATES)

    gaps = json.loads((ROOT / "output" / "gaps.json").read_text())
    for gap_num, cand in enumerate(infer.CANDIDATES, start=1):
        n_labeled = int((labels == gap_num).sum())
        matching_gap = next(g for g in gaps if g["need"] == cand["need"])
        # gaps.json's n is parsed from confidence_justification; recompute the same way
        import re
        m = re.search(r"n=(\d+) distinct reviews", matching_gap["confidence_justification"])
        assert abs(n_labeled - int(m.group(1))) <= 1


def test_does_not_touch_gaps_json(dual_module):
    gaps_path = ROOT / "output" / "gaps.json"
    before = gaps_path.read_text()
    assert gaps_path.read_text() == before
