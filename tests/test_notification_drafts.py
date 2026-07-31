"""
Tests for scripts/08_draft_notifications.py. Purely additive -- does not
touch output/gaps.json, output/gaps.md, or output/team_routing.json.

Usage: python -m pytest tests/test_notification_drafts.py -v
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GAPS_PATH = ROOT / "output" / "gaps.json"
ROUTING_PATH = ROOT / "output" / "team_routing.json"
NOTIF_DIR = ROOT / "output" / "team_notifications"

REQUIRED_TEXT_SECTIONS = [
    "Subject:", "Confidence:", "Verdict:", "Evidence:",
    "Related roadmap issue(s):", "Suggested next step:", "Why this was routed to",
]
REQUIRED_JSON_KEYS = {
    "gap_rank", "team", "to_address", "subject", "confidence", "verdict",
    "need", "evidence", "roadmap_refs", "suggested_next_step",
    "routing_reasoning", "body_text",
}


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def draft_module():
    module = _load_module("08_draft_notifications.py")
    module.main()
    return module


def test_every_gap_produces_a_txt_and_json_draft(draft_module):
    gaps = json.loads(GAPS_PATH.read_text())
    routing = {r["gap_rank"]: r for r in json.loads(ROUTING_PATH.read_text())}
    for gap in gaps:
        team_slug = routing[gap["rank"]]["team"].lower()
        txt_path = NOTIF_DIR / f"gap_{gap['rank']}_{team_slug}.txt"
        json_path = NOTIF_DIR / f"gap_{gap['rank']}_{team_slug}.json"
        assert txt_path.exists() and txt_path.stat().st_size > 0
        assert json_path.exists() and json_path.stat().st_size > 0


def test_txt_drafts_have_all_required_sections():
    for txt_path in NOTIF_DIR.glob("*.txt"):
        text = txt_path.read_text()
        assert text.strip(), f"{txt_path} is empty"
        for section in REQUIRED_TEXT_SECTIONS:
            assert section in text, f"{txt_path} missing section {section!r}"


def test_txt_draft_addressed_to_a_valid_team():
    routing_module = _load_module("07_route_to_team.py")
    valid_slugs = {t.lower() for t in routing_module.TEAMS}
    for txt_path in NOTIF_DIR.glob("*.txt"):
        first_line = txt_path.read_text().splitlines()[0]
        assert first_line.startswith("To: ")
        team_part = first_line.split("@")[0].replace("To: ", "").replace("-", "_")
        assert team_part in valid_slugs


def test_json_drafts_have_required_keys():
    for json_path in NOTIF_DIR.glob("*.json"):
        data = json.loads(json_path.read_text())
        assert REQUIRED_JSON_KEYS <= set(data.keys())
        assert data["confidence"] >= 0.5
        assert len(data["evidence"]) >= 2
        assert data["body_text"].strip()


def test_subject_lines_are_specific_not_generic():
    for json_path in NOTIF_DIR.glob("*.json"):
        data = json.loads(json_path.read_text())
        subject = data["subject"]
        assert subject.startswith("[Gap Analysis]")
        assert "user reports" in subject
        assert len(subject) > 30


def test_does_not_touch_gaps_json_or_routing():
    before_gaps = GAPS_PATH.read_text()
    before_routing = ROUTING_PATH.read_text()
    _load_module("08_draft_notifications.py").main()
    assert GAPS_PATH.read_text() == before_gaps
    assert ROUTING_PATH.read_text() == before_routing
