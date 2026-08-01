# LESSONS.md

Durable corrections from real mistakes made in this repo's session history. Format: mistake, fix, rule going forward. Kept short and honest on purpose — a handful of real entries beats a padded list.

## 1. Env vars set in one terminal are invisible to a Claude Code process already running in another

**Mistake:** An `export` run in one terminal window was assumed to be visible to a Claude Code session already running in a different window/process — it wasn't, because each process inherits its environment at launch, not live.

**Fix:** Verify the variable is actually set in the running process's own environment (e.g. a length/existence check) before trusting that an export happened, instead of assuming it propagated.

**Rule going forward:** Never assume an environment variable change made outside the current process is visible to it. Check it from inside the process that needs it.

## 2. A regex or `max(key=...)` over a set with a tied/degenerate result can silently pick the wrong element

**Mistake:** Two real, separate instances this session:
- `scripts/14_weight_calibration.py`: at the grid-search-optimal (pure-corroboration) weighting, 3 rejected candidates tie at score 1.0. `max(range(...), key=lambda i: best_rejected_scores[i])` silently returned the *first* tied candidate (`video-crash`), not the one the report's own prose meant to name (`moderation-appeal`) — producing a factually wrong "Key finding" sentence that shipped to the report before being caught on a re-read.
- `scripts/15_adversarial_verify.py`: `re.search(r"n=(\d+)", ...)` matched inside `"corroboration=1.0"` (the literal substring `"...n=1.0"`) before ever reaching the real `"(n=287 ...)"` later in the same string — every gap's recomputed-n cross-check reported `shipped n=1`, a wrong "DRIFT DETECTED" flag on all 4 gaps until the regex was tightened to `r"\(n=(\d+)"`.

**Fix:** Both were caught only by reading the actual generated report text against known ground truth, not by the code running without errors (it ran fine both times — the output was just wrong).

**Rule going forward:** Any regex or `max/min(key=...)` used to extract a specific fact for a human-readable report must be run against the real string/data it will actually see, with the result eyeballed against a hand-known-correct value, before that output goes into a shipped report — "no exception raised" is not "correct." Ties at a degenerate optimum are a specific case worth checking for explicitly, not just assuming uniqueness.

## 3. A script that fully regenerates its own output file will silently destroy hand-added narrative text in that file

**Mistake:** `output/semantic_validation.md` and `output/bootstrap_stability.md` each had a manually-written synthesis/investigation section added by hand after a script run. Re-running the same script (to pick up a parameter or bug fix) overwrote the whole file from scratch, silently deleting that hand-added section along with everything else.

**Fix:** Re-added the synthesis text by hand again after each rerun, each time it happened.

**Rule going forward:** Don't hand-edit a file that a script's `main()` fully rewrites (`OUT_PATH.write_text(...)` on the whole file) and expect the edit to survive a rerun. Either move durable narrative into the script itself (as a string the script writes), or into a separate file the script doesn't touch — not into the generated file directly.

## 4. sklearn's default algorithm choice can hide an order-of-magnitude runtime difference

**Mistake:** `HDBSCAN`'s default `algorithm="auto"` took ~46s for a single fit on this project's 8,359×384 embedding matrix, versus ~2s for `algorithm="brute"` with identical cluster output (see `output/clustering_tuning_report.md`, "Selected method" section). A hyperparameter sweep run at the default setting would have made an 18-setting grid impractically slow, and the runtime difference was invisible until a single fit was actually timed.

**Rule going forward:** Before running any grid sweep, time one fit at realistic data size first. Don't assume a library's default is the fast path, especially for algorithms with multiple exact/approximate backends (`algorithm=`, `n_jobs=`, exact-vs-approximate solvers) — profile once, then decide whether a sweep is tractable, not the other way around.
