"""
Tests for scripts/15_adversarial_verify.py. Pure arithmetic/text checks --
no embedding model needed, runs fast. Does not touch output/gaps.json or
any shipped-gap data.

Usage: python -m pytest tests/test_adversarial_verify.py -v
"""
from datetime import datetime
from pathlib import Path
import importlib.util
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def adv_module():
    return _load_module("15_adversarial_verify.py")


@pytest.fixture(scope="module")
def infer_module():
    return _load_module("03_infer_gaps.py")


def test_extract_keywords_drops_stopwords_and_short_words(adv_module):
    kw = adv_module.extract_keywords("The user can't log in to the app on Android")
    assert "the" not in kw
    assert "can't" in kw
    assert "android" in kw
    assert "to" not in kw  # too short / stopword


def test_shipped_n_from_justification_ignores_corroboration_equals_one(adv_module):
    """Regression test for a real bug found during development: a bare
    r"n=(\\d+)" regex matches inside "corroboration=1.0" (the "...n=1.0"
    substring) before ever reaching the real "(n=287 ...)" later in the
    string, silently returning 1 instead of 287."""
    gap = {
        "confidence_justification": (
            "corroboration=1.0 (n=287 distinct reviews / 15 cap) * 0.35 = 0.35; "
            "signal_count=1.0 (n=287 / 100 cap) * 0.25 = 0.25"
        )
    }
    assert adv_module.shipped_n_from_justification(gap) == 287


def test_shipped_n_from_justification_returns_none_when_absent(adv_module):
    assert adv_module.shipped_n_from_justification({"confidence_justification": "no n here"}) is None


def test_tail_silence_days_computes_gap_to_dataset_max(adv_module, infer_module):
    reviews = [
        {"id": "r1", "text": "x", "timestamp": "2025-01-01T00:00:00", "rating": 1},
        {"id": "r2", "text": "y", "timestamp": "2025-01-10T00:00:00", "rating": 1},
    ]
    candidate = {"review_filter": lambda r: True}
    # infer.parse_ts produces naive datetimes for timestamps with no "Z"/offset
    # (matching the real reviews.jsonl format) -- dataset_max must be naive too.
    dataset_max = datetime(2025, 1, 20)
    days = adv_module.tail_silence_days(candidate, reviews, infer_module, dataset_max)
    assert days == 10  # gap between r2 (latest match) and dataset_max


def test_tail_silence_days_returns_none_for_no_matches(adv_module, infer_module):
    candidate = {"review_filter": lambda r: False}
    dataset_max = datetime(2025, 1, 20)
    assert adv_module.tail_silence_days(candidate, [], infer_module, dataset_max) is None


def test_roadmap_overlap_candidates_excludes_declared_refs(adv_module):
    candidate = {
        "need": "Users cannot remove followers or lock their account against spam",
        "roadmap_refs": [{"number": 100}],
    }
    roadmap = [
        {"source_type": "github_issue", "metadata": {"number": 100},
         "text": "Remove followers and lock account spam feature"},  # declared, must be excluded
        {"source_type": "github_issue", "metadata": {"number": 200},
         "text": "Remove followers and lock account against spam requests"},  # undeclared, should surface
        {"source_type": "github_issue", "metadata": {"number": 300},
         "text": "Completely unrelated issue about dark mode theming"},
    ]
    result = adv_module.roadmap_overlap_candidates(candidate, roadmap)
    numbers = [r["number"] for r in result]
    assert 100 not in numbers
    assert 200 in numbers
    assert 300 not in numbers


def test_evidence_integrity_check_flags_non_verbatim_excerpt(adv_module, infer_module):
    gap = {
        "evidence": [
            {"id": "review-x", "excerpt_or_paraphrase": "this text does not match at all", "weight": "primary"},
            {"id": "review-y", "excerpt_or_paraphrase": "real prefix", "weight": "corroborating"},
        ]
    }
    reviews_by_id = {
        "review-x": {"text": "completely different actual review text"},
        "review-y": {"text": "real prefix and then more text after it"},
    }
    diversity_ok, issues = adv_module.evidence_integrity_check(gap, reviews_by_id, {}, infer_module)
    assert any("review-x" in i for i in issues)
    assert not any("review-y" in i for i in issues)


def test_evidence_integrity_check_flags_missing_id(adv_module, infer_module):
    gap = {"evidence": [{"id": "review-missing", "excerpt_or_paraphrase": "x", "weight": "primary"},
                         {"id": "github-issue-1", "excerpt_or_paraphrase": "y", "weight": "corroborating"}]}
    diversity_ok, issues = adv_module.evidence_integrity_check(gap, {}, {}, infer_module)
    assert any("review-missing" in i and "not found" in i for i in issues)


def test_primary_rating_check_computes_cluster_mean_and_delta(adv_module):
    candidate = {"review_filter": lambda r: True}
    reviews = [
        {"id": "review-a", "rating": 1}, {"id": "review-b", "rating": 1}, {"id": "review-c", "rating": 5},
    ]
    reviews_by_id = {r["id"]: r for r in reviews}
    # primary_rating_check only considers review-* ids (github issues have no rating)
    gap = {"evidence": [{"id": "review-c", "weight": "primary"}]}
    cluster_mean, primary_id, primary_rating = adv_module.primary_rating_check(gap, candidate, reviews, reviews_by_id)
    assert cluster_mean == pytest.approx(7 / 3)
    assert primary_id == "review-c"
    assert primary_rating == 5


def test_find_by_need_prefix_matches_regardless_of_truncation_length(adv_module):
    table = {"Users can't sign in because keyboard": ("100", "100")}
    need = "Users can't sign in because keyboard flashes and closes immediately."
    assert adv_module.find_by_need_prefix(table, need) == ("100", "100")
    assert adv_module.find_by_need_prefix(table, "Something unrelated") is None


def test_recompute_n_matches_filter_count(adv_module):
    candidate = {"review_filter": lambda r: r["id"] in ("a", "b")}
    reviews = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    assert adv_module.recompute_n(candidate, reviews) == 2


def test_real_run_produces_report_covering_all_4_shipped_gaps(adv_module, infer_module):
    """End-to-end smoke test on real data -- confirms the report actually
    gets written and mentions every shipped gap's need text."""
    adv_module.main()
    out_path = ROOT / "output" / "adversarial_verification.md"
    text = out_path.read_text()
    for candidate in infer_module.CANDIDATES:
        assert candidate["need"][:60] in text
    assert "Survived adversarial review" in text
    assert "video-playback-crash" in text  # calibration case must be cited


def test_does_not_touch_gaps_json():
    gaps_path = ROOT / "output" / "gaps.json"
    before = gaps_path.read_text()
    assert gaps_path.read_text() == before
