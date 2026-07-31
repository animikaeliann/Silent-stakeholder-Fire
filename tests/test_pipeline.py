"""
Tests for the normalize -> fetch -> infer pipeline, per SPEC.md.

Covers: normalized-record schema conformance (SPEC.md §2), the gap output
contract's hard evidence rule (SPEC.md §3), the confidence floor (SPEC.md
§4), that confidence_justification actually shows the rubric math, and that
a fabricated zero-evidence gap is correctly rejected by the pipeline's own
validation function (not just by convention).

Usage: python -m pytest tests/test_pipeline.py -v
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REVIEWS_PATH = ROOT / "data/normalized/reviews.jsonl"
ROADMAP_PATH = ROOT / "data/normalized/roadmap.jsonl"
GAPS_PATH = ROOT / "output/gaps.json"
REJECTED_PATH = ROOT / "output/rejected_candidates.jsonl"

VALID_SOURCE_TYPES = {"review", "ticket", "github_issue", "github_milestone"}
VALID_VERDICTS = {"IGNORED", "UNDER-PRIORITIZED", "MISUNDERSTOOD"}


def _load_module(filename):
    """Numeric-prefixed filenames (03_infer_gaps.py) aren't valid module
    identifiers, so load by path instead of `import`."""
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def infer_gaps_module():
    return _load_module("03_infer_gaps.py")


def _load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


# ---------------------------------------------------------------------------
# Schema conformance (SPEC.md §2)
# ---------------------------------------------------------------------------

def _assert_normalized_record_schema(rec):
    assert set(["id", "source_type", "source_dataset", "text", "timestamp", "rating", "metadata"]) <= set(rec.keys())
    assert isinstance(rec["id"], str) and rec["id"]
    assert rec["source_type"] in VALID_SOURCE_TYPES
    assert isinstance(rec["source_dataset"], str) and rec["source_dataset"]
    assert isinstance(rec["text"], str)
    assert rec["timestamp"] is None or isinstance(rec["timestamp"], str)
    assert rec["rating"] is None or isinstance(rec["rating"], (int, float))
    assert isinstance(rec["metadata"], dict)


def test_reviews_schema_conformance():
    reviews = _load_jsonl(REVIEWS_PATH)
    assert len(reviews) > 0
    for rec in reviews:
        _assert_normalized_record_schema(rec)
        assert rec["source_type"] == "review"
        assert rec["id"].startswith("review-play-")


def test_roadmap_schema_conformance():
    roadmap = _load_jsonl(ROADMAP_PATH)
    assert len(roadmap) > 0
    for rec in roadmap:
        _assert_normalized_record_schema(rec)
        assert rec["source_type"] in {"github_issue", "github_milestone"}


def test_normalized_ids_are_unique_within_each_file():
    for path in (REVIEWS_PATH, ROADMAP_PATH):
        recs = _load_jsonl(path)
        ids = [r["id"] for r in recs]
        assert len(ids) == len(set(ids)), f"duplicate ids in {path}"


# ---------------------------------------------------------------------------
# Gap output contract (SPEC.md §3) and confidence rubric (SPEC.md §4)
# ---------------------------------------------------------------------------

def test_gaps_file_is_nonempty_and_well_formed():
    gaps = json.loads(GAPS_PATH.read_text())
    assert isinstance(gaps, list) and len(gaps) > 0
    for gap in gaps:
        for key in ("rank", "need", "confidence", "confidence_justification", "verdict",
                    "verdict_justification", "evidence", "roadmap_refs",
                    "rejected_alternative_explanations"):
            assert key in gap, f"missing key {key!r} in gap {gap.get('need')!r}"
        assert gap["verdict"] in VALID_VERDICTS


def test_every_gap_has_at_least_two_evidence_entries_from_two_source_types(infer_gaps_module):
    gaps = json.loads(GAPS_PATH.read_text())
    for gap in gaps:
        assert len(gap["evidence"]) >= 2, f"gap {gap['need']!r} has fewer than 2 evidence entries"
        assert infer_gaps_module.evidence_diversity_ok(gap["evidence"]), (
            f"gap {gap['need']!r} evidence is not from >=2 distinct source_types"
        )


def test_no_gap_ships_under_confidence_threshold():
    gaps = json.loads(GAPS_PATH.read_text())
    for gap in gaps:
        assert gap["confidence"] >= 0.5, f"gap {gap['need']!r} shipped at {gap['confidence']} < 0.5"


def test_confidence_is_rounded_to_nearest_0_05():
    gaps = json.loads(GAPS_PATH.read_text())
    for gap in gaps:
        scaled = gap["confidence"] / 0.05
        assert abs(scaled - round(scaled)) < 1e-9, f"{gap['confidence']} is not a multiple of 0.05"


def test_confidence_justification_shows_rubric_math():
    gaps = json.loads(GAPS_PATH.read_text())
    for gap in gaps:
        justification = gap["confidence_justification"]
        assert justification and isinstance(justification, str)
        for factor in ("corroboration", "signal_count", "latency", "roadmap_disconfirmation"):
            assert factor in justification, f"{factor!r} not shown in justification for {gap['need']!r}"
        # rubric math must show actual numbers, not just factor names
        assert any(ch.isdigit() for ch in justification)


def test_gaps_ranked_by_descending_confidence():
    gaps = json.loads(GAPS_PATH.read_text())
    confidences = [g["confidence"] for g in gaps]
    assert confidences == sorted(confidences, reverse=True)
    assert [g["rank"] for g in gaps] == list(range(1, len(gaps) + 1))


# ---------------------------------------------------------------------------
# Rejection log (SPEC.md §6)
# ---------------------------------------------------------------------------

def test_rejected_candidates_log_has_reasons():
    rejected = _load_jsonl(REJECTED_PATH)
    assert len(rejected) > 0
    for rec in rejected:
        assert rec.get("need")
        assert rec.get("reason") and len(rec["reason"]) > 20


# ---------------------------------------------------------------------------
# Falsification: a fabricated zero-evidence gap must be rejected
# ---------------------------------------------------------------------------

def test_fabricated_zero_evidence_gap_is_rejected(infer_gaps_module):
    fabricated_gap = {
        "rank": 1,
        "need": "Users secretly want a pony feature.",
        "confidence": 0.9,
        "confidence_justification": "trust me",
        "verdict": "IGNORED",
        "verdict_justification": "trust me",
        "evidence": [],
        "roadmap_refs": [],
        "rejected_alternative_explanations": "none considered",
    }
    assert not infer_gaps_module.evidence_diversity_ok(fabricated_gap["evidence"])


def test_fabricated_single_source_type_gap_is_rejected(infer_gaps_module):
    """Two reviews but no roadmap-side evidence still fails the >=2-source-types rule."""
    fabricated_gap_evidence = [
        {"id": "review-play-00001", "excerpt_or_paraphrase": "made up", "weight": "primary"},
        {"id": "review-play-00002", "excerpt_or_paraphrase": "also made up", "weight": "corroborating"},
    ]
    assert not infer_gaps_module.evidence_diversity_ok(fabricated_gap_evidence)


def test_real_gap_evidence_passes_diversity_check(infer_gaps_module):
    real_evidence = [
        {"id": "review-play-00001", "excerpt_or_paraphrase": "x", "weight": "primary"},
        {"id": "github-issue-6264", "excerpt_or_paraphrase": "y", "weight": "corroborating"},
    ]
    assert infer_gaps_module.evidence_diversity_ok(real_evidence)
