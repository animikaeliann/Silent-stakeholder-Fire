# Rubric sensitivity analysis

Baseline weights: corroboration=0.35, signal_count=0.25, latency=0.20, roadmap_disconfirmation=0.20. Perturbed 21 ways: each weight individually shifted by ±0.05 and ±0.10 (others rescaled proportionally to keep the vector summing to 1.0), plus 5 random weight vectors (seeded, reproducible).

## Headline finding

**Stable.** Across all 21 perturbations, the top-3 ranking order of the shipped gaps never changes, and no candidate crosses the 0.5 ship/no-ship threshold in either direction relative to baseline. The confidence numbers in gaps.json are not an artifact of the specific weight choice.

## Confidence range per candidate across all perturbations

| Candidate | Shipped? | n reviews | Baseline conf. | Min | Max |
|---|---|---|---|---|---|
| Users can't sign in or join the waitlist because the on-scre… | yes | 287 | 0.95 | 0.95 | 1.0 |
| Users have no way to stop bot/spam accounts from following t… | yes | 67 | 0.85 | 0.8 | 0.9 |
| Follower counts and follower lists don't reflect reality: bl… | yes | 15 | 0.65 | 0.6 | 0.75 |
| App crashes every time a user tries to open/play a video (fu… | no | 32 | 0.7 | 0.6 | 0.75 |
| Users want the ability to turn on notifications for individu… | no | 21 | 0.7 | 0.65 | 0.75 |
| Accounts get suspended/labeled with no explanation or a slow… | no | 78 | 0.95 | 0.9 | 0.95 |

## Rank-order stability (shipped gaps only)

Baseline order: login-keyboard-dismissal > no-private-account-remove-follower > follower-count-block-desync

No perturbation changed this order.

## Threshold-crossing events (0.5 ship/no-ship line)

No candidate crosses the 0.5 line under any tested perturbation.

## Note on the pre-rejected candidates included here

The two falsified candidates (video-playback crash, per-account notifications) were rejected on evidence-based falsification grounds, not a low confidence score -- their rubric confidence here is for sensitivity testing only and does not mean they should ship; the falsification evidence (documented in output/rejected_candidates.jsonl) stands independently of this analysis.
The moderation-appeal-transparency candidate scores 0.95 confidence under the baseline rubric (above the 0.5 ship line) using a reconstructed cluster and no roadmap match (roadmap_disconfirmation=1.0, since no search for an adjacent issue was performed before it was excluded). This candidate was excluded on SPEC.md §7 non-goal grounds (confounded with partisan sentiment), independent of what the rubric alone would say -- a reminder that the rubric formalizes corroboration/scale/persistence/roadmap-neglect, not scope-fit, and a human judgment call is still load-bearing on top of it.
