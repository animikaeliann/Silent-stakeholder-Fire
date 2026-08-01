# CLAUDE.md

## What this is

A gap-analysis pipeline for Bluesky (`bluesky-social/social-app`): it cross-references 8,359 Play Store reviews against the project's GitHub issues/milestones to find user needs the roadmap is ignoring, under-prioritizing, or misunderstanding, scores each candidate with an auditable rubric, and ships only the survivors as `output/gaps.json` / `output/gaps.md` with an evidence trail.

## Commands (verified working on this machine, just now)

**Docker** (recommended — verified end-to-end just now):
```
docker compose build
docker compose up -d
curl http://127.0.0.1:8420/health   # -> {"status":"ok","gaps_loaded":4,"rejected_loaded":3}
curl http://127.0.0.1:8420/         # -> frontend HTML (same-origin, no CORS needed)
docker compose down
```
Also verified through the running container: `/gaps` (4 gaps), `/rejected` (3), `/routing` (4), `/notifications/1`. Base image is `python:3.9-slim`, matched to this machine's actual local Python (`python3 --version` → 3.9.6), not guessed. Port 8420 is mapped host:container 1:1 in `docker-compose.yml` — same collision-avoidance reasoning as the bare-metal port below applies.

**Backend, bare-metal fallback** (FastAPI):
```
python3 -m uvicorn backend.app:app --reload --port 8420
```
Then `curl http://127.0.0.1:8420/health` → `{"status":"ok","gaps_loaded":4,"rejected_loaded":3}`.
Use `python3`, not `python` — bare `python` does not exist on this machine (`command not found`). Use `python3 -m uvicorn`, not a bare `uvicorn` binary — the console script isn't on `PATH` here.

**Frontend**: no build step. Through Docker, it's served same-origin at `/` by `backend/app.py` (a `FileResponse` route) — open `http://localhost:8420`. Opened directly as `frontend/index.html` (`file://`, bare-metal fallback), it talks to `http://127.0.0.1:8420` instead — `API_BASE` in `frontend/index.html` switches on `window.location.protocol` to pick whichever is correct, so the same file works both ways.

**Full test suite**:
```
python3 -m pytest tests/ backend/tests/ -q
```
Currently 104 passed (verified this run).

**Regenerate `output/gaps.json` / `gaps.md` from scratch**:
```
python3 scripts/01_normalize_reviews.py
python3 scripts/03_infer_gaps.py
python3 scripts/04_generate_report.py
```
Verified just now: this reproduces `output/gaps.json`, `output/rejected_candidates.jsonl`, and `output/gaps.md` byte-for-byte (`git diff --stat` empty on all three afterward), because steps 01/03/04 only depend on the local, already-committed `data/raw/bluesky_reviews.csv` and `data/normalized/roadmap.jsonl`.
Caveat: `01_normalize_reviews.py` *appends* to `logs/filtered.jsonl` (`open(..., "a")`) rather than overwriting it — running it twice duplicates that log's entries. `git checkout -- logs/filtered.jsonl` after a verification run if you don't want the duplicate lines committed.
`scripts/02_fetch_github_roadmap.py` (which produces `data/normalized/roadmap.jsonl`) is **not** included above on purpose: it hits the live GitHub REST API and is not reproducible on demand — re-running it can pull different issue state (labels, milestones, `updated_at`) than what `gaps.json` was originally scored against, which would silently change `roadmap_disconfirmation` scores. Don't re-run it casually; if you do, treat the resulting `gaps.json` diff as a real finding to review, not noise.

## The locked contract

`SPEC.md` is the source of truth for the normalized schema, the gap object contract, the confidence rubric (weights, rounding, ship threshold), verdict definitions, and non-goals. Don't duplicate it here — read it directly, it's 90 lines.

## Protected files

`output/gaps.json` and `output/gaps.md` are the shipped demo baseline (currently 4 gaps: login-keyboard-dismissal, CAPTCHA-blocks-signup, follower-count-block-desync, no-private-account-remove-follower). **Do not modify their content, or the rejected-candidates evidence/scores, as a side effect of other work** — not by re-running the pipeline casually, not as pipeline drift, not as an incidental part of a tuning/analysis task. Any proposed change to what's shipped comes back to the user for explicit approval first. Read-only analysis passes (scripts 05, 06, 10-15) are fine; anything that would rewrite `output/gaps.json`'s content is not, without asking first.

## Pipeline stage inventory (`scripts/`)

1. `01_normalize_reviews.py` — normalize `data/raw/bluesky_reviews.csv` into the schema locked in SPEC.md §2.
2. `02_fetch_github_roadmap.py` — fetch issues/milestones for `bluesky-social/social-app` from the GitHub REST API (live network; see caveat above).
3. `03_infer_gaps.py` — gap inference pipeline (the full SPEC.md loop): ingest normalized reviews + roadmap, score, falsify, ship survivors.
4. `04_generate_report.py` — render `output/gaps.json` into `output/gaps.md`, a ranked human-readable report.
5. `05_rubric_sensitivity.py` — rubric sensitivity / defense-readiness analysis. Purely additive, does not modify shipped output.
6. `06_semantic_clustering_check.py` — semantic clustering validation pass, independent of the keyword-based pipeline.
7. `07_route_to_team.py` — team-routing classifier for shipped gaps. Purely additive.
8. `08_draft_notifications.py` — draft a notification email per routed gap. Purely additive.
9. `09_send_notifications.py` — demo-safe sending of the drafts in `output/team_notifications/*.json` (dry-run by default).
10. `10_tune_clustering.py` — hyperparameter tuning for the semantic-clustering validation pass (silhouette + stability joint objective).
11. `11_bootstrap_stability.py` — bootstrap stability analysis proving the shipped gaps are stable patterns, not resampling artifacts.
12. `12_dual_method_discovery.py` — dual-method candidate discovery: keyword-based vs. tuned-semantic-based, with formal agreement metrics (ARI/NMI).
13. `13_semantic_falsification.py` — semantic-similarity upgrade to the falsification check (embedding-based resolution-language detection).
14. `14_weight_calibration.py` — exploratory data-driven calibration of the confidence rubric's 4 hand-picked weights. Exploratory only, not applied to shipped gaps.
15. `15_adversarial_verify.py` — independent try-to-refute pass against each shipped gap (tail-silence timing, broader roadmap rescan, evidence integrity/representativeness, corroboration-count integrity), run as a separate pass from the one that proposed each gap.

Every script above 04 is additive/read-only analysis layered on top of the SPEC.md-locked core pipeline (01-04) — none of them are supposed to change `output/gaps.json`'s content, only add new report files alongside it.
