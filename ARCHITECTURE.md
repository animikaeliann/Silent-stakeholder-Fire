# Architecture — The Silent Stakeholder

## What this is

A pipeline that cross-references 8,359 Bluesky Play Store reviews against the live `bluesky-social/social-app` GitHub issue tracker to surface user needs the roadmap has ignored, under-prioritized, or misunderstood — each shipped with a calibrated confidence score (rubric math shown, not asserted), a verdict, and a traceable evidence trail back to specific reviews and issues. No external LLM call anywhere in the gap-inference step; clustering and scoring are deterministic and auditable.

## Pipeline

```
┌───────────────────────┐        ┌────────────────────────────────┐
│ data/raw/              │        │ GitHub REST API                  │
│ bluesky_reviews.csv    │        │ (unauthenticated, 60 req/hr)     │
└───────────┬────────────┘        └────────────────┬─────────────────┘
            │                                       │
            ▼                                       ▼
  01_normalize_reviews.py             02_fetch_github_roadmap.py
            │                                       │           (no shared input --
            ▼                                       ▼            independent / parallel)
  data/normalized/                    data/normalized/
  reviews.jsonl                       roadmap.jsonl
            │                                       │
            └───────────────────┬───────────────────┘
                                 ▼
                       03_infer_gaps.py
           cluster → cross-check roadmap → falsify → score
                                 │
                                 ▼
        output/gaps.json  +  output/rejected_candidates.jsonl
                                 │
             ┌───────────────────┼────────────────────────┐
             ▼                   ▼                         ▼
  04_generate_report.py   07_route_to_team.py      (validation branch,
             │                   │                   see below --
             ▼                   ▼                   NOT on this path)
     output/gaps.md    output/team_routing.json
                                 │
                                 ▼
                  08_draft_notifications.py
                                 │
                                 ▼
          output/team_notifications/*.{txt,json}
                    │                        │
                    │                        ▼
                    │              09_send_notifications.py
                    │              (optional; dry-run by default,
                    │               real send is opt-in + gated)
                    ▼
      backend/app.py (FastAPI, port 8420)
      GET /gaps /gaps/{rank} /rejected /routing /notifications/{rank}
                    │
                    ▼
      frontend/index.html (fetch() only, no build step)
```

**Independent validation branch** (verification, not critical path — reads `gaps.json`, never writes back to it):

```
output/gaps.json ──┬──► 05_rubric_sensitivity.py ──► output/rubric_sensitivity.md
                    └──► 06_semantic_clustering_check.py ──► output/semantic_validation.md
```

## Scripts

| Script | Does | Reads | Writes |
|---|---|---|---|
| `01_normalize_reviews.py` | Normalizes raw reviews into the locked schema; every raw record produces exactly one normalized record, no silent drops | `data/raw/bluesky_reviews.csv` | `data/normalized/reviews.jsonl`, `logs/filtered.jsonl` |
| `02_fetch_github_roadmap.py` | Fetches issues + milestones from GitHub, drops PRs, normalizes to the same schema | GitHub REST API | `data/raw/github_issues.json`, `data/raw/github_milestones.json`, `data/normalized/roadmap.jsonl`, `logs/filtered.jsonl` |
| `03_infer_gaps.py` | Clusters review signals by keyword, cross-checks the roadmap, runs an adversarial falsification pass, scores confidence, accepts/rejects | `data/normalized/reviews.jsonl`, `data/normalized/roadmap.jsonl` | `output/gaps.json`, `output/rejected_candidates.jsonl` |
| `04_generate_report.py` | Renders the ranked, evidence-linked human-readable report for the live defense | `output/gaps.json`, `output/rejected_candidates.jsonl`, `data/normalized/roadmap.jsonl` | `output/gaps.md` |
| `05_rubric_sensitivity.py` | *(validation)* Recomputes confidence under 21 perturbed rubric-weight vectors to check the ranking isn't an artifact of the specific weights | `output/gaps.json` inputs (via imported candidate definitions), normalized data | `output/rubric_sensitivity.md` |
| `06_semantic_clustering_check.py` | *(validation)* Independent embedding-based (local sentence-transformer) second opinion on the keyword clusters; searches for missed candidates | `data/normalized/reviews.jsonl` | `output/semantic_validation.md` |
| `07_route_to_team.py` | Classifies each gap to an engineering team via GitHub label signal, falling back to weighted keyword matching | `output/gaps.json`, `data/normalized/roadmap.jsonl` | `output/team_routing.json` |
| `08_draft_notifications.py` | Drafts a plain-text + structured-JSON notification email per routed gap | `output/gaps.json`, `output/team_routing.json` | `output/team_notifications/gap_{rank}_{team}.{txt,json}` |
| `09_send_notifications.py` | Demo-safe sender: dry run by default; real send requires 3 env vars and always goes to one override address | `output/team_notifications/*.json` | Nothing by default; an email, only if fully configured |

## Data flow

| Location | Format | Contents |
|---|---|---|
| `data/raw/` | CSV, raw JSON | User-provided review export; raw GitHub API responses |
| `data/normalized/` | JSONL (one record/line) | Reviews and roadmap items, both conformed to the SPEC.md §2 schema |
| `logs/` | JSONL | Every record dropped or flagged during normalization/fetch, with a reason — never a silent drop |
| `output/` | JSON, JSONL, Markdown | Shipped gaps, rejected candidates, human-readable report, routing decisions, notification drafts, validation reports |

## Tests

46 tests total, all reading/writing scratch or already-generated data — none regenerate the shipped `gaps.json`/`gaps.md` baseline.

| File | Count | Verifies |
|---|---|---|
| `tests/test_pipeline.py` | 13 | Normalized-record schema conformance; every gap has ≥2 evidence entries from ≥2 distinct source types (hard rule); no gap ships under 0.5 confidence; confidence math is actually shown, not asserted; rank ordering; rejected-candidates log has real reasons; fabricated zero-evidence/single-source gaps are correctly rejected |
| `tests/test_sensitivity.py` | 5 | Perturbed weight vectors still sum to 1.0; all candidates carry required fields; `compute_confidence` stays in `[0,1]`; the script runs end-to-end and produces a report; the report never touches `gaps.json` |
| `tests/test_semantic_clustering.py` | 4 | Embeddings are L2-normalized; cosine similarity stays in range; a small-sample run produces a valid report; it never touches the real output files |
| `tests/test_routing.py` | 5 | Every gap gets a valid team + reasoning; routing covers every gap rank; an unmatched candidate correctly falls back to "Unassigned / Needs Triage"; a GitHub label signal takes priority over keyword matching when present; doesn't touch `gaps.json` |
| `tests/test_notification_drafts.py` | 6 | Every gap produces a `.txt` and `.json` draft; all required sections present; addressed to a valid team; JSON has required keys; subject lines are specific, not generic; doesn't touch `gaps.json`/`team_routing.json` |
| `tests/test_send_notifications.py` | 5 | Default behavior is a dry run; a missing `SMTP_HOST` falls back to dry run even with the other two vars set; an invalid email address falls back to dry run; a real (mocked) send only ever goes to the override address; a missing drafts directory doesn't crash |
| `backend/tests/test_api.py` | 8 | `/health`; `/gaps` matches the SPEC.md §3 schema; `/gaps/{rank}` valid + 404; `/rejected`; `/routing` returns valid records; `/notifications/{rank}` valid + 404 |

## Design decisions worth defending

**Keyword clustering *and* semantic validation, not just one.** Gaps were shipped using deterministic keyword matching — reproducible, auditable, no ML dependency, satisfies the "no external API" constraint on gap inference. But keyword matching can miss paraphrases. A separate local-embedding pass (`06`) acts as a second opinion after the fact: it confirmed both already-excluded candidates were correctly excluded, flagged that gap #1's true cluster may be modestly undercounted, and surfaced two genuinely new candidates (a CAPTCHA blocking sign-up, feed/scroll instability) — neither auto-added to `gaps.json`, both left for a human judgment call.

**Four rubric factors, not one score.** Corroboration (is this real — saturates fast at n=15) and signal_count (how big is this — saturates slow at n=100) are deliberately different functions of the same review count, so "enough independent people said this" and "how large is this at scale" don't collapse into one number. Latency rewards persistence over a flash-in-the-pan. Roadmap_disconfirmation is a fixed, auditable lookup (labels/milestone/staleness), not a vibe. The 0.35/0.25/0.20/0.20 weighting was stress-tested across 21 perturbed weight vectors (`05`): the top-3 ranking never changes and nothing crosses the 0.5 ship line — the evidence is doing the work, not the specific weights.

**Notification sending is gated and dry-run by default.** The routed team addresses (`android-client@...`, `trust-safety@...`) are fictional placeholders, never meant to receive real mail — a real version would need the target org's actual opt-in and a verified contact list, which this project deliberately doesn't attempt to obtain or guess. Real sending requires three explicit env vars (`DEMO_SEND_EMAIL`, `DEMO_RECIPIENT_OVERRIDE`, `SMTP_HOST`) and routes every email to one override address regardless of which team a gap was routed to.

**GitHub fetch is open-issues-only, unauthenticated.** No `GITHUB_TOKEN`/`gh auth` was available in the environment this was built in. Unauthenticated REST API is capped at 60 req/hr; `bluesky-social/social-app` has 2,300+ open issues alone, so open+closed history wasn't feasible in one run within that budget. Scoped to open issues + all milestones, logged explicitly as a reasoned decision (not a silent drop) — and each gap's falsification check (does complaint volume taper off over time) partially compensates for not being able to see issues that were already fixed and closed.

## Known limitations

- **Roadmap has no closed-issue history** (unauthenticated fetch scope, above) — IGNORED/UNDER-PRIORITIZED verdicts can't fully distinguish "nobody filed this" from "somebody filed and fixed this, then closed it."
- **Review corpus ends 2025-04-20**; the roadmap reflects live state as of each run — a multi-month blind window where sentiment could shift unseen.
- **Clustering is deterministic keyword matching**, which will miss paraphrased complaints that don't share the matched keywords — the semantic-validation pass mitigates this but doesn't eliminate it.
- **One legitimate-looking candidate was excluded outright**, not scored down: a moderation-appeals complaint inseparable from partisan sentiment in the corpus, ruled out of scope by SPEC.md §7.
- **The rubric alone isn't sufficient**: the sensitivity pass found the excluded moderation-appeals candidate would score 0.95 confidence on the formula alone — a reminder the rubric formalizes corroboration/scale/persistence/roadmap-neglect, not scope-fit, and human judgment still sits on top of it.
- **Two semantic-validation findings are unresolved**: a CAPTCHA-blocks-signup cluster and a feed/scroll-instability cluster were surfaced but never roadmap-cross-checked, scored, or falsification-tested — they are not gaps, just leads.
