"""
Tests for scripts/05_rubric_sensitivity.py. Does not touch output/gaps.json
or output/rejected_candidates.jsonl -- only exercises the sensitivity script
and its own output file.

Usage: python -m pytest tests/test_sensitivity.py -v
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SENSITIVITY_OUT = ROOT / "output" / "rubric_sensitivity.md"


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sensitivity_module():
    return _load_module("05_rubric_sensitivity.py")


def test_perturbations_sum_to_one(sensitivity_module):
    perturbations = sensitivity_module.build_perturbation_set()
    assert len(perturbations) > 1
    for name, weights in perturbations.items():
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-6, f"{name} weights sum to {total}, not 1.0"
        for v in weights.values():
            assert v >= 0


def test_all_candidates_have_required_fields(sensitivity_module):
    for cand in sensitivity_module.ALL_CANDIDATES:
        assert "id" in cand and "need" in cand and "review_filter" in cand and "roadmap_refs" in cand
        assert "shipped" in cand


def test_compute_confidence_in_valid_range(sensitivity_module):
    infer = sensitivity_module.infer
    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    roadmap = infer.load_jsonl(infer.ROADMAP_PATH)
    roadmap_by_number = {
        r["metadata"]["number"]: r for r in roadmap if r["source_type"] == "github_issue"
    }
    for cand in sensitivity_module.ALL_CANDIDATES:
        conf, n = sensitivity_module.compute_confidence(
            cand, reviews, roadmap_by_number, sensitivity_module.BASE_WEIGHTS
        )
        assert 0.0 <= conf <= 1.0
        assert n >= 0


def test_script_runs_and_produces_report(sensitivity_module):
    sensitivity_module.main()
    assert SENSITIVITY_OUT.exists()
    text = SENSITIVITY_OUT.read_text()
    assert len(text) > 200
    for heading in ("Headline finding", "Confidence range per candidate",
                    "Rank-order stability", "Threshold-crossing events"):
        assert heading in text


def test_report_does_not_touch_gaps_output():
    """Guard against accidental regeneration of the demo-ready baseline."""
    gaps_path = ROOT / "output" / "gaps.json"
    rejected_path = ROOT / "output" / "rejected_candidates.jsonl"
    before_gaps = gaps_path.read_text()
    before_rejected = rejected_path.read_text()
    _load_module("05_rubric_sensitivity.py").main()
    assert gaps_path.read_text() == before_gaps
    assert rejected_path.read_text() == before_rejected
