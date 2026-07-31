"""
Tests for scripts/07_route_to_team.py. Purely additive -- does not touch
output/gaps.json or output/gaps.md.

Usage: python -m pytest tests/test_routing.py -v
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GAPS_PATH = ROOT / "output" / "gaps.json"
ROUTING_PATH = ROOT / "output" / "team_routing.json"


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def routing_module():
    return _load_module("07_route_to_team.py")


def test_every_gap_gets_a_valid_team_and_reasoning(routing_module):
    routing_module.main()
    routing = json.loads(ROUTING_PATH.read_text())
    gaps = json.loads(GAPS_PATH.read_text())
    assert len(routing) == len(gaps)
    for rec in routing:
        assert rec["team"] in routing_module.TEAMS
        assert isinstance(rec["reasoning"], str) and len(rec["reasoning"]) > 20
        assert rec["signal_used"] in ("label", "keyword")
        assert isinstance(rec["cc_teams"], list)
        for cc in rec["cc_teams"]:
            assert cc in routing_module.TEAMS
            assert cc != rec["team"]


def test_routing_covers_every_gap_rank(routing_module):
    routing = json.loads(ROUTING_PATH.read_text())
    gaps = json.loads(GAPS_PATH.read_text())
    routed_ranks = {r["gap_rank"] for r in routing}
    gap_ranks = {g["rank"] for g in gaps}
    assert routed_ranks == gap_ranks


def test_keyword_signal_never_silently_empty_on_unclear(routing_module):
    fabricated_gap = {
        "need": "Something totally generic that matches nothing in particular.",
        "evidence": [{"excerpt_or_paraphrase": "no useful signal here at all whatsoever"}],
    }
    team, scores, matched_terms, also_plausible = routing_module.keyword_signal(fabricated_gap)
    assert team == "UNCLEAR"
    assert also_plausible == []


def test_label_signal_takes_priority_when_present(routing_module):
    fabricated_gap = {
        "roadmap_refs": [{"id": "github-issue-999999"}],
        "need": "totally unrelated text with android keyboard login words",
        "evidence": [],
    }
    fabricated_roadmap_by_id = {
        "github-issue-999999": {"metadata": {"labels": ["area:moderation"]}}
    }
    team, matched_label, checked_issues = routing_module.label_signal(fabricated_gap, fabricated_roadmap_by_id)
    assert team == "TRUST_SAFETY"
    assert matched_label == "area:moderation"


def test_does_not_touch_gaps_json():
    before = GAPS_PATH.read_text()
    _load_module("07_route_to_team.py").main()
    assert GAPS_PATH.read_text() == before
