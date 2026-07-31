"""
Minimal FastAPI service over the pipeline's output files. No database --
this is a 24hr hackathon demo; output/gaps.json and
output/rejected_candidates.jsonl are read once at startup and served
straight out of memory.

Run: uvicorn backend.app:app --reload --port 8000
"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent
GAPS_PATH = ROOT / "output" / "gaps.json"
REJECTED_PATH = ROOT / "output" / "rejected_candidates.jsonl"


def load_gaps():
    return json.loads(GAPS_PATH.read_text())


def load_rejected():
    with open(REJECTED_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


app = FastAPI(title="The Silent Stakeholder — Gap Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

GAPS = load_gaps()
REJECTED = load_rejected()


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
