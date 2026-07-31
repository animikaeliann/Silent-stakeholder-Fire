"""
API tests for backend/app.py using FastAPI's TestClient.

Usage: python -m pytest backend/tests/test_api.py -v
Requires: pip install pytest httpx
"""
from fastapi.testclient import TestClient

from backend.app import app, GAPS

client = TestClient(app)

VALID_VERDICTS = {"IGNORED", "UNDER-PRIORITIZED", "MISUNDERSTOOD"}
GAP_KEYS = {
    "rank", "need", "confidence", "confidence_justification", "verdict",
    "verdict_justification", "evidence", "roadmap_refs",
    "rejected_alternative_explanations",
}


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["gaps_loaded"] == len(GAPS)


def test_gaps_returns_valid_list_matching_spec_schema():
    resp = client.get("/gaps")
    assert resp.status_code == 200
    gaps = resp.json()
    assert isinstance(gaps, list) and len(gaps) > 0
    for gap in gaps:
        assert GAP_KEYS <= set(gap.keys())
        assert gap["verdict"] in VALID_VERDICTS
        assert gap["confidence"] >= 0.5
        assert len(gap["evidence"]) >= 2


def test_gap_by_valid_rank_returns_the_right_gap():
    all_gaps = client.get("/gaps").json()
    target = all_gaps[0]
    resp = client.get(f"/gaps/{target['rank']}")
    assert resp.status_code == 200
    assert resp.json() == target


def test_gap_by_invalid_rank_returns_404():
    resp = client.get("/gaps/9999")
    assert resp.status_code == 404


def test_rejected_returns_200_and_a_list():
    resp = client.get("/rejected")
    assert resp.status_code == 200
    rejected = resp.json()
    assert isinstance(rejected, list) and len(rejected) > 0
    for rec in rejected:
        assert "need" in rec and "reason" in rec
