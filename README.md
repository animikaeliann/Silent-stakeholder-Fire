# The Silent Stakeholder — Bluesky Gap Analysis

Pipeline: `scripts/01_normalize_reviews.py` -> `scripts/02_fetch_github_roadmap.py`
-> `scripts/03_infer_gaps.py` -> `scripts/04_generate_report.py`, output at
`output/gaps.json` / `output/gaps.md`. See `SPEC.md` for the locked contract.

See `ARCHITECTURE.md` for a full pipeline breakdown.

## Running the API

```
pip install -r requirements.txt
python -m uvicorn backend.app:app --reload --port 8420
```

Use `python -m uvicorn`, not a bare `uvicorn` — pip installs its console
script under `~/Library/Python/<ver>/bin`, which usually isn't on `PATH`.

Port **8420**, not 8000: on at least one dev machine, `localhost:8000` /
`127.0.0.1:8000` silently landed on Docker Desktop's backend service (bound
to `[::]:8000`, dual-stack, so it swallows IPv4 loopback too whenever
nothing else holds that exact address) instead of this API, returning its
`{"message":"Unauthorized"}` with no indication anything was wrong. 8420
avoided every collision found when scanning for a free port on this box —
if it's taken on yours, pick another and update `frontend/index.html`'s
`API_BASE` to match.

Endpoints: `GET /health`, `GET /gaps`, `GET /gaps/{rank}`, `GET /rejected`.

## Running the frontend

Open `frontend/index.html` directly in a browser (no build step) while the
API above is running on port 8420.

## Tests

```
pip install pytest httpx
python -m pytest tests/ backend/tests/ -v
```
