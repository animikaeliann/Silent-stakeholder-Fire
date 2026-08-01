"""
Minimal FastAPI service over the pipeline's output files. No database --
this is a 24hr hackathon demo; output/gaps.json and
output/rejected_candidates.jsonl are read once at startup and served
straight out of memory.

Run: python -m uvicorn backend.app:app --reload --port 8420
(port 8420, not 8000 -- Docker Desktop's backend service on this box binds
[::]:8000 dual-stack and will silently intercept loopback traffic on 8000)
"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent.parent
GAPS_PATH = ROOT / "output" / "gaps.json"
REJECTED_PATH = ROOT / "output" / "rejected_candidates.jsonl"
ROUTING_PATH = ROOT / "output" / "team_routing.json"
NOTIFICATIONS_DIR = ROOT / "output" / "team_notifications"
FRONTEND_INDEX = ROOT / "frontend" / "index.html"


def load_gaps():
    return json.loads(GAPS_PATH.read_text())


def load_rejected():
    with open(REJECTED_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_routing():
    if not ROUTING_PATH.exists():
        return []
    return json.loads(ROUTING_PATH.read_text())


def load_notifications():
    """Map gap_rank -> parsed notification draft, read from
    output/team_notifications/gap_{rank}_{team}.json (team slug varies per
    gap, so this globs rather than assuming a filename)."""
    notifications = {}
    if not NOTIFICATIONS_DIR.exists():
        return notifications
    for path in NOTIFICATIONS_DIR.glob("gap_*.json"):
        data = json.loads(path.read_text())
        rank = data.get("gap_rank")
        if rank is not None:
            notifications[rank] = data
    return notifications


app = FastAPI(title="The Silent Stakeholder — Gap Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

GAPS = load_gaps()
REJECTED = load_rejected()
ROUTING = load_routing()
NOTIFICATIONS = load_notifications()


@app.get("/")
def frontend_index():
    """Serves frontend/index.html at the API's own origin -- lets Docker
    (or any same-origin deployment) skip the file:// + CORS workflow
    entirely. Additive: doesn't touch any existing API route, and the
    file:// double-click workflow (frontend/index.html opened directly in
    a browser) is untouched and still works via the CORS middleware above."""
    return FileResponse(FRONTEND_INDEX)


@app.get("/health")
def health():
    return {"status": "ok", "gaps_loaded": len(GAPS), "rejected_loaded": len(REJECTED)}


@app.get("/gaps")
def get_gaps():
    return GAPS


@app.get("/gaps/{rank}")
def get_gap(rank: int):
    for gap in GAPS:
        if gap["rank"] == rank:
            return gap
    raise HTTPException(status_code=404, detail=f"no gap with rank {rank}")


@app.get("/rejected")
def get_rejected():
    return REJECTED


@app.get("/routing")
def get_routing():
    return ROUTING


@app.get("/notifications/{gap_rank}")
def get_notification(gap_rank: int):
    if gap_rank not in NOTIFICATIONS:
        raise HTTPException(status_code=404, detail=f"no drafted notification for gap {gap_rank}")
    return NOTIFICATIONS[gap_rank]
