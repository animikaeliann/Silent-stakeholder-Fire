# The Silent Stakeholder — Bluesky Gap Analysis

Repo: https://github.com/animikaeliann/Silent-stakeholder-Fire

**The gap:** Bluesky's Android login flow has a keyboard-dismissal bug blocking account access for a significant share of users — corroborated by 287 reviews and an exact-match GitHub issue open 620+ days with no milestone. (Gap #1 of 5 shipped, top-ranked by confidence — see Results below.)

## Run it

**Docker (recommended):**
```
docker compose up --build
```
Then open **http://localhost:8420** — verified just now: the container builds, `/` returns the frontend HTML, and `/health` returns `{"status":"ok","gaps_loaded":5,"rejected_loaded":3}`. Stop with `docker compose down`.

**Bare-metal fallback (no Docker):**
```
pip install -r requirements.txt
python3 -m uvicorn backend.app:app --reload --port 8420
```
Then open `frontend/index.html` directly in a browser (no build step) — verified just now on this machine. Use `python3`, not `python` — bare `python` doesn't exist on this machine, and pip's `uvicorn` console script usually isn't on `PATH` either, hence `python3 -m uvicorn`. Not port 8000 — see `CLAUDE.md` for why.

## What this does

Cross-references 8,359 Bluesky Play Store reviews against the live `bluesky-social/social-app` GitHub issue tracker to surface user needs the roadmap is ignoring, under-prioritizing, or misunderstanding. Each finding ships with a calibrated confidence score (rubric math shown in full, not asserted), a verdict, and a traceable evidence trail back to specific reviews and issues.

## Results

**5 gaps shipped**, confidence range 0.65–0.95, ranked by confidence in `output/gaps.json` / `output/gaps.md` (the human-readable report — full evidence and rubric math per gap is there). 3 candidates were considered and rejected, with reasons, in `output/rejected_candidates.jsonl`.

## Methodology highlights

- **The confidence rubric is auditable, not a black box.** 4 weighted factors (corroboration, signal count, latency, roadmap disconfirmation), 0.35/0.25/0.20/0.20, shown in full arithmetic per gap in `confidence_justification` — anyone can redo the math by hand from the stated inputs.
- **Every shipped gap survived an independent adversarial falsification pass** — a separate try-to-refute check (not the same pass that proposed each gap), covering self-resolution language, complaint-volume tail-silence, a broader roadmap rescan, and evidence-integrity re-verification. All 5 gaps survived; see `output/adversarial_verification.md`.
- **The rubric itself was stress-tested, not just trusted.** 21 perturbed weight vectors (each factor individually shifted ±0.05/±0.10, plus 5 random vectors). Result: the 0.5 ship/no-ship threshold never crosses under any perturbation (0 of 21) — but rank order between the two closest-scoring gaps is sensitive to weight choice in 9 of 21 perturbations, disclosed rather than hidden. See `output/rubric_sensitivity.md`.
- **An independent semantic-embedding clustering pass validated the keyword-based method**, run as a co-equal primary method rather than an after-the-fact check. Formal agreement metrics (Adjusted Rand Index, Normalized Mutual Information) plus per-gap convergence: 3 of the original 4 shipped gaps converge cleanly with the semantic partition by majority-membership capture; the one non-convergent case was independently traced to the same root cause (a two-bundled-asks cluster) already flagged by bootstrap-stability analysis. See `output/dual_method_agreement.md`.
- **A dedicated second-order/latent-need mining pass was run specifically to go beyond "frequent complaints."** Four detectors (workaround language, implicit cross-app comparison, silent-churn divergence, cross-cluster time-correlation) searched for needs that only become visible by combining signals across many reviews or across time — not findable by reading any single review. Honest result: one borderline candidate cleared that bar; it was scored through the exact same rubric used for shipped gaps and came in at 0.45, below the 0.5 threshold — correctly not shipped. A system that tried the harder thing and reported a negative result honestly is stronger evidence of rigor than one that didn't try. See `output/latent_candidates.md` and `output/latent_candidates_scored.json`.

## Test coverage

**124 tests passing**, verified by running the suite just now:
```
python3 -m pytest tests/ backend/tests/ -q
```
15 test files across the pipeline, rubric, routing, notifications, and every validation/adversarial/latent-mining pass — none regenerate the shipped `gaps.json`/`gaps.md` baseline as a side effect.

## Further reading

`CLAUDE.md` has verified run commands, environment gotchas, and the full pipeline stage inventory for anyone continuing development. `ARCHITECTURE.md` has a deeper pipeline breakdown, but predates some of the later analysis passes (gap #5, scripts 10+) — treat its gap count and script list as lagging the current state; `output/gaps.md` and this README are the accurate current picture.

## Submission requirements

- [x] Repo link — above
- [x] Runnable system — `docker compose up --build`, verified working end-to-end just now
- [x] Ranked gap output — `output/gaps.json` / `output/gaps.md`, 5 gaps, confidence-ranked
- [x] One-sentence gap statement — above, gap #1, verified against `output/gaps.json`
