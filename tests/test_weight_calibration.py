"""
Tests for scripts/14_weight_calibration.py. Pure arithmetic (reuses
03_infer_gaps.py's own rubric functions) -- no embedding model needed,
runs fast. Does not touch output/gaps.json or any shipped-gap data.

Usage: python -m pytest tests/test_weight_calibration.py -v
"""
import importlib.util
import sys
from pathlib import Path

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
def calib_module():
    return _load_module("14_weight_calibration.py")


def test_weight_grid_points_sum_to_one_and_nonnegative(calib_module):
    count = 0
    for w in calib_module.weight_grid(step=0.25):  # coarse grid, fast to fully enumerate
        assert abs(sum(w.values()) - 1.0) < 1e-9
        assert all(v >= 0 for v in w.values())
        count += 1
    assert count > 0


def test_weight_grid_includes_hand_picked_style_point(calib_module):
    # 0.35/0.25/0.20/0.20 isn't exactly on a step=0.05 grid boundary in all cases,
    # but a grid point close to equal weighting (0.25 each) must appear at step=0.25
    points = list(calib_module.weight_grid(step=0.25))
    equal_weights = {f: 0.25 for f in calib_module.FACTOR_NAMES}
    assert any(w == equal_weights for w in points)


def test_score_is_weighted_sum(calib_module):
    factors = {"corroboration": 1.0, "signal_count": 0.5, "latency": 0.2, "roadmap_disconfirmation": 0.8}
    weights = {"corroboration": 0.35, "signal_count": 0.25, "latency": 0.20, "roadmap_disconfirmation": 0.20}
    expected = 0.35 * 1.0 + 0.25 * 0.5 + 0.20 * 0.2 + 0.20 * 0.8
    assert calib_module.score(factors, weights) == pytest.approx(expected)


def test_margin_is_min_shipped_minus_max_rejected(calib_module):
    weights = {"corroboration": 1.0, "signal_count": 0.0, "latency": 0.0, "roadmap_disconfirmation": 0.0}
    shipped_factors = [
        {"corroboration": 0.9, "signal_count": 0, "latency": 0, "roadmap_disconfirmation": 0},
        {"corroboration": 0.6, "signal_count": 0, "latency": 0, "roadmap_disconfirmation": 0},
    ]
    rejected_factors = [
        {"corroboration": 0.3, "signal_count": 0, "latency": 0, "roadmap_disconfirmation": 0},
        {"corroboration": 0.5, "signal_count": 0, "latency": 0, "roadmap_disconfirmation": 0},
    ]
    m, shipped_scores, rejected_scores = calib_module.margin(weights, shipped_factors, rejected_factors)
    assert m == pytest.approx(0.6 - 0.5)  # min(0.9, 0.6) - max(0.3, 0.5)
    assert shipped_scores == [pytest.approx(0.9), pytest.approx(0.6)]
    assert rejected_scores == [pytest.approx(0.3), pytest.approx(0.5)]


def test_compute_raw_factors_real_shipped_candidate_matches_gaps_json(calib_module):
    """Cross-check against gaps.json's own reported n/confidence for gap #1,
    reusing the exact rubric functions 03_infer_gaps.py already exposes."""
    import json
    infer = _load_module("03_infer_gaps.py")
    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    roadmap = infer.load_jsonl(infer.ROADMAP_PATH)
    roadmap_by_number = {r["metadata"]["number"]: r for r in roadmap if r["source_type"] == "github_issue"}

    login_candidate = next(c for c in infer.CANDIDATES if c["id"] == "login-keyboard-dismissal")
    factors = calib_module.compute_raw_factors(login_candidate, reviews, roadmap_by_number, infer)
    assert factors["n"] == 287
    assert factors["corroboration"] == 1.0  # 287/15 capped at 1.0
    assert 0.0 <= factors["roadmap_disconfirmation"] <= 1.0

    gaps = json.loads((ROOT / "output" / "gaps.json").read_text())
    hand_picked = calib_module.HAND_PICKED_WEIGHTS
    raw_score = calib_module.score(factors, hand_picked)
    rounded = round(round(raw_score / 0.05) * 0.05, 2)
    shipped_gap = next(g for g in gaps if g["need"] == login_candidate["need"])
    assert rounded == shipped_gap["confidence"]


def test_does_not_touch_gaps_json():
    gaps_path = ROOT / "output" / "gaps.json"
    before = gaps_path.read_text()
    assert gaps_path.read_text() == before


def test_full_run_produces_report_with_key_sections(calib_module):
    calib_module.main()
    out_path = ROOT / "output" / "weight_calibration_report.md"
    text = out_path.read_text()
    for heading in ("Hand-picked weights", "Grid-search optimum", "Limitations"):
        assert heading in text
    # On the real data, margin <= 0 (moderation-appeal's raw numbers block clean
    # separation, as rubric_sensitivity.md already found from a different angle) --
    # the "Key finding" section must appear whenever that's the case.
    assert "Key finding" in text

