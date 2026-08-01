# CLAUDE.md

## What this is

A gap-analysis pipeline for Bluesky (`bluesky-social/social-app`): it cross-references 8,359 Play Store reviews against the project's GitHub issues/milestones to find user needs the roadmap is ignoring, under-prioritizing, or misunderstanding, scores each candidate with an auditable rubric, and ships only the survivors as `output/gaps.json` / `output/gaps.md` with an evidence trail.

## Commands (verified working on this machine, just now)

**Backend** (FastAPI):
```
python3 -m uvicorn backend.app:app --reload --port 8420
```
Then `curl http://127.0.0.1:8420/health` → `{"status":"ok","gaps_loaded":4,"rejected_loaded":3}`.
Use `python3`, not `python` — bare `python` does not exist on this machine (`command not found`). Use `python3 -m uvicorn`, not a bare `uvicorn` binary — the console script isn't on `PATH` here.

**Frontend**: no build step, just open `frontend/index.html` in a browser while the backend above is running. It talks to `http://127.0.0.1:8420` (hardcoded in `frontend/index.html`'s `API_BASE`).

**Full test suite**:
```
python3 -m pytest tests/ backend/tests/ -q
```
Currently 91 passed (verified this run).

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

Every script above 04 is additive/read-only analysis layered on top of the SPEC.md-locked core pipeline (01-04) — none of them are supposed to change `output/gaps.json`'s content, only add new report files alongside it.
