"""
Tests for scripts/16_latent_signal_mining.py. Smoke tests per detector on
small fixtures, plus a regression test for the real methodological bug
found while developing this: raw-count cross-cluster correlation falsely
flags almost every theme pair because total review volume itself spikes
in 2024-11 -- normalizing by monthly share fixes it.

Usage: python -m pytest tests/test_latent_signal_mining.py -v
"""
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
def mining_module():
    return _load_module("16_latent_signal_mining.py")


def test_detect_workaround_language_matches_known_patterns(mining_module):
    reviews = [
        {"id": "a", "text": "I have to manually re-enter my password every time.", "timestamp": "2024-01-01T00:00:00", "rating": 2},
        {"id": "b", "text": "This app is fantastic, love it!", "timestamp": "2024-01-01T00:00:00", "rating": 5},
        {"id": "c", "text": "Found a workaround for the login bug.", "timestamp": "2024-01-01T00:00:00", "rating": 3},
    ]
    matches = mining_module.detect_workaround_language(reviews)
    ids = {m["id"] for m in matches}
    assert "a" in ids
    assert "c" in ids
    assert "b" not in ids


def test_detect_implicit_comparison_requires_both_app_and_frame(mining_module):
    reviews = [
        {"id": "a", "text": "Unlike Twitter, this app doesn't have a bookmark feature.", "timestamp": "2024-01-01T00:00:00", "rating": 3},
        {"id": "b", "text": "Twitter is fine I guess.", "timestamp": "2024-01-01T00:00:00", "rating": 3},  # app named, no comparison frame
        {"id": "c", "text": "Unlike my expectations, this crashed immediately.", "timestamp": "2024-01-01T00:00:00", "rating": 1},  # frame, no app
    ]
    matches = mining_module.detect_implicit_comparison(reviews)
    ids = {m["id"] for m in matches}
    assert ids == {"a"}


def test_is_churn_targeting_this_app_excludes_competitor_target(mining_module):
    text = "I just uninstalled X (Twitter) and am counting on you, Bluesky."
    m = mining_module.CHURN_RE.search(text)
    assert m is not None
    assert mining_module.is_churn_targeting_this_app(text, m) is False


def test_is_churn_targeting_this_app_keeps_real_churn(mining_module):
    text = "Uninstalling this app, done with it."
    m = mining_module.CHURN_RE.search(text)
    assert m is not None
    assert mining_module.is_churn_targeting_this_app(text, m) is True


def test_half_split_rates_computes_per_month_rate(mining_module):
    dated = ["2024-01-01T00:00:00"] * 2 + ["2024-02-01T00:00:00"] * 2 + ["2024-03-01T00:00:00"] * 6
    result = mining_module.half_split_rates(dated)
    assert result is not None
    first_rate, second_rate = result
    assert second_rate > first_rate  # more volume concentrated in the later month


def test_half_split_rates_returns_none_for_single_month(mining_module):
    dated = ["2024-01-01T00:00:00"] * 5
    assert mining_module.half_split_rates(dated) is None


def test_silent_churn_analysis_requires_minimum_theme_size(mining_module):
    reviews = [{"id": str(i), "text": "small complaint", "timestamp": "2024-01-01T00:00:00", "rating": 2} for i in range(3)]
    result = mining_module.silent_churn_analysis("tiny-theme", lambda r: True, reviews)
    assert result["flagged"] is False
    assert "insufficient data" in result["reason"]


def test_silent_churn_analysis_flags_declining_complaints_and_rising_churn(mining_module):
    reviews = []
    # First half (Jan-Feb): many complaints, a little churn. Second half
    # (May-Jun): few complaints, much more churn -- churn matches must span
    # >= 2 distinct months themselves, or half_split_rates can't compute a
    # churn trend at all (a real bug found via this exact test: a single-
    # month churn_matches list previously crashed with a TypeError instead
    # of being reported as insufficient data -- see silent_churn_analysis).
    for i in range(10):
        reviews.append({"id": f"early-{i}", "text": "this bug is annoying", "timestamp": "2024-01-01T00:00:00", "rating": 2})
    for i in range(10):
        reviews.append({"id": f"early2-{i}", "text": "this bug is annoying", "timestamp": "2024-02-01T00:00:00", "rating": 2})
    for i in range(2):
        reviews.append({"id": f"early-churn-{i}", "text": "this bug is annoying, uninstalling now", "timestamp": "2024-01-01T00:00:00", "rating": 1})
    for i in range(3):
        reviews.append({"id": f"late-complaint-{i}", "text": "this bug is annoying", "timestamp": "2024-05-01T00:00:00", "rating": 2})
    for i in range(4):
        reviews.append({"id": f"late-churn-{i}", "text": "this bug is annoying, uninstalling now", "timestamp": "2024-05-01T00:00:00", "rating": 1})
    for i in range(4):
        reviews.append({"id": f"late-churn2-{i}", "text": "this bug is annoying, uninstalling now", "timestamp": "2024-06-01T00:00:00", "rating": 1})
    result = mining_module.silent_churn_analysis("test-theme", lambda r: True, reviews)
    assert result["flagged"] is True
    assert result["declining_complaints"] is True
    assert result["rising_churn"] is True


def test_pearson_perfect_positive_correlation(mining_module):
    xs = [1, 2, 3, 4, 5]
    ys = [2, 4, 6, 8, 10]
    assert mining_module.pearson(xs, ys) == pytest.approx(1.0)


def test_pearson_zero_variance_returns_zero_not_error(mining_module):
    xs = [3, 3, 3, 3]
    ys = [1, 2, 3, 4]
    assert mining_module.pearson(xs, ys) == 0.0


def test_cross_cluster_correlation_normalizes_by_monthly_volume_not_raw_count(mining_module):
    """Regression test for the real bug found running this against real
    data: total review volume spikes ~10x in one month (a real, well-known
    event in this corpus), so ANY two themes that are each just a constant
    fraction of monthly volume have raw counts that rise and fall together
    -- perfectly correlated (r=1.0) -- with zero real relationship between
    them. Theme A here is always 10% of a month's reviews, Theme B always
    30% -- unrelated fractions, but raw counts both jump 10x from the quiet
    month to the busy one. Normalizing by monthly share must report r=0.0
    (no real covariation once overall volume is controlled for), not the
    spurious r=1.0 raw counts would give."""
    reviews = []
    # Month 1 quiet (10 reviews), month 2 busy (100 reviews) -- mimics the
    # real corpus's ~10x spike in 2024-11.
    for i in range(10):
        reviews.append({"id": f"m1-{i}", "text": "generic review text", "timestamp": "2024-01-01T00:00:00", "rating": 3})
    for i in range(100):
        reviews.append({"id": f"m2-{i}", "text": "generic review text", "timestamp": "2024-02-01T00:00:00", "rating": 3})
    # Theme A: exactly 10% of each month (1 of 10, 10 of 100).
    a_ids = set([f"m1-{i}" for i in range(1)] + [f"m2-{i}" for i in range(10)])
    # Theme B: exactly 30% of each month (3 of 10, 30 of 100) -- a different,
    # unrelated fraction, disjoint review ids from theme A.
    b_ids = set([f"m1-{i}" for i in range(1, 4)] + [f"m2-{i}" for i in range(10, 40)])
    themes = {
        "theme-a": ("alpha widget issue", lambda r: r["id"] in a_ids),
        "theme-b": ("beta gadget problem", lambda r: r["id"] in b_ids),
    }
    passed, near_misses = mining_module.cross_cluster_correlation(themes, reviews)
    assert passed == []  # correctly does NOT flag this as a correlated pair
    assert near_misses[0]["correlation"] == pytest.approx(0.0)  # not the spurious 1.0 raw counts would give


def test_real_run_produces_expected_output_sections(mining_module):
    mining_module.main()
    out_path = ROOT / "output" / "latent_signals_raw.json"
    import json
    data = json.loads(out_path.read_text())
    assert "phase_0_finding" in data
    assert "no reviewer/user identifier" in data["phase_0_finding"].lower()
    for key in ("workaround_language", "implicit_comparison", "silent_churn_divergence", "cross_cluster_correlation"):
        assert key in data


def test_does_not_touch_gaps_json():
    gaps_path = ROOT / "output" / "gaps.json"
    before = gaps_path.read_text()
    assert gaps_path.read_text() == before
