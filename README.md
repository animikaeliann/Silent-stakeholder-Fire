# The Silent Stakeholder — Bluesky Gap Analysis

Pipeline: `scripts/01_normalize_reviews.py` -> `scripts/02_fetch_github_roadmap.py`
-> `scripts/03_infer_gaps.py` -> `scripts/04_generate_report.py`, output at
`output/gaps.json` / `output/gaps.md`. See `SPEC.md` for the locked contract.

## Running the API

```
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 8000
```

Endpoints: `GET /health`, `GET /gaps`, `GET /gaps/{rank}`, `GET /rejected`.

## Running the frontend

Open `frontend/index.html` directly in a browser (no build step) while the
API above is running on port 8000.

## Tests

```
pip install pytest httpx
python -m pytest tests/ backend/tests/ -v
```
