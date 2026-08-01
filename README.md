# The Silent Stakeholder — Bluesky Gap Analysis

Repo: https://github.com/animikaeliann/Silent-stakeholder-Fire

**The gap:** Bluesky's Android login flow has a keyboard-dismissal bug blocking account access for a significant share of users — corroborated by 287 reviews and an exact-match GitHub issue open 620+ days with no milestone.

Pipeline: `scripts/01_normalize_reviews.py` -> `scripts/02_fetch_github_roadmap.py`
-> `scripts/03_infer_gaps.py` -> `scripts/04_generate_report.py`, output at
`output/gaps.json` / `output/gaps.md`. See `SPEC.md` for the locked contract.

See `ARCHITECTURE.md` for a full pipeline breakdown.

## Run with Docker (recommended)

```
docker compose up --build
```

Then open **http://localhost:8420** — the container serves both the API
and the frontend from the same origin (verified end-to-end: every
endpoint below returns real data, and `/` returns the frontend HTML), so
there's no separate frontend step and no CORS setup needed. Stop with
`docker compose down`.

## Running the API manually (fallback, no Docker)

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

Endpoints: `GET /health`, `GET /gaps`, `GET /gaps/{rank}`, `GET /rejected`,
`GET /routing`, `GET /notifications/{gap_rank}`.

## Running the frontend manually (fallback, no Docker)

Open `frontend/index.html` directly in a browser (no build step) while the
API above is running on port 8420. `API_BASE` detects the `file://`
protocol and points at `http://127.0.0.1:8420` in that case only — the
Docker path above serves the same file same-origin instead, via a relative
path.

## Tests

```
pip install pytest httpx
python -m pytest tests/ backend/tests/ -v
```
