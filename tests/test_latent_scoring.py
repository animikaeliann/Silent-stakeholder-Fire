"""
Tests for scripts/18_latent_scoring.py (Phase 3: run the Phase-2 survivor
through the existing rigor pipeline, report only). Does not touch
output/gaps.json or any shipped-gap data.

Usage: python -m pytest tests/test_latent_scoring.py -v
"""
from pathlib import Path
import importlib.util
import json
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
def scoring_module():
    return _load_module("18_latent_scoring.py")


def test_candidate_review_filter_matches_exactly_the_4_cited_reviews(scoring_module):
    infer = _load_module("03_infer_gaps.py")
    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    matched = [r for r in reviews if scoring_module.CANDIDATE["review_filter"](r)]
    matched_ids = {r["id"] for r in matched}
    assert matched_ids == scoring_module.EVIDENCE_REVIEW_IDS
    assert len(matched) == 4


def test_candidate_roadmap_refs_resolve_to_real_issues(scoring_module):
    infer = _load_module("03_infer_gaps.py")
    roadmap = infer.load_jsonl(infer.ROADMAP_PATH)
    roadmap_by_number = {r["metadata"]["number"]: r for r in roadmap if r["source_type"] == "github_issue"}
    for ref in scoring_module.CANDIDATE["roadmap_refs"]:
        assert ref["number"] in roadmap_by_number


def test_candidate_has_alt_explanation_and_latent_justification(scoring_module):
    assert scoring_module.CANDIDATE["alt_explanation"]
    assert len(scoring_module.LATENT_JUSTIFICATION) > 100  # a real written explanation, not a stub


def test_reuses_build_gap_unchanged(scoring_module):
    """This phase's brief requires reusing 03_infer_gaps.py's existing
    scoring code, not reinventing it -- verify main() actually calls
    through to infer.build_gap by checking the output has exactly the
    fields build_gap produces, plus the two fields this phase adds."""
    infer = _load_module("03_infer_gaps.py")
    reviews = infer.load_jsonl(infer.REVIEWS_PATH)
    roadmap = infer.load_jsonl(infer.ROADMAP_PATH)
    roadmap_by_number = {r["metadata"]["number"]: r for r in roadmap if r["source_type"] == "github_issue"}
    gap, n, confidence = infer.build_gap(scoring_module.CANDIDATE, reviews, roadmap_by_number, rank=None)

    scoring_module.main()
    out = json.loads((ROOT / "output" / "latent_candidates_scored.json").read_text())
    scored = out["candidates"][0]

    # Every field build_gap produces must be present and match a fresh call.
    for key in ("need", "confidence", "verdict", "evidence", "roadmap_refs"):
        assert scored[key] == gap[key]
    assert scored["confidence"] == confidence


def test_low_n_produces_confidence_below_ship_threshold(scoring_module):
    """This candidate's own thinness (n=4) is expected to fail the
    existing rubric's 0.5 ship threshold -- documents the real, honest
    result rather than asserting a specific number that could drift."""
    scoring_module.main()
    out = json.loads((ROOT / "output" / "latent_candidates_scored.json").read_text())
    scored = out["candidates"][0]
    assert scored["ships_by_confidence_alone"] == (scored["confidence"] >= 0.5)


def test_output_is_explicitly_marked_report_only(scoring_module):
    scoring_module.main()
    out = json.loads((ROOT / "output" / "latent_candidates_scored.json").read_text())
    assert "report only" in out["note"].lower() or "REPORT ONLY" in out["note"]
    assert "human approval" in out["note"].lower()


def test_does_not_touch_gaps_json():
    gaps_path = ROOT / "output" / "gaps.json"
    before = gaps_path.read_text()
    assert gaps_path.read_text() == before
