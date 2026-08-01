# Weight calibration report (exploratory)

**Exploratory only -- nothing here is applied to gaps.json.** Grid search (step 0.05, 1771 points on the weight simplex) maximizing `margin(w) = min(shipped confidence) - max(rejected confidence)` using each candidate's raw, pre-rounding rubric factors -- already computed by 03_infer_gaps.py, not re-derived here.

## Objective and inputs

- 5 shipped candidates, 3 rejected candidates (the 3 reconstructed in output/rubric_sensitivity.md).
- Margin is worst-case (min shipped vs. max rejected), not a difference of averages -- a weighting that separates the average well but leaves the weakest shipped gap scoring below the strongest rejected candidate is not what "the rubric correctly separates accepted from rejected" should mean.

## Hand-picked weights (shipped)

`{'corroboration': 0.35, 'signal_count': 0.25, 'latency': 0.2, 'roadmap_disconfirmation': 0.2}` -- margin = **-0.2731**

| Candidate | Kind | Raw score |
|---|---|---|
| Users can't sign in or join the waitlist because t… | shipped | 0.9600 |
| Users have no way to stop bot/spam accounts from f… | shipped | 0.8475 |
| Follower counts and follower lists don't reflect r… | shipped | 0.6719 |
| A broken CAPTCHA/verification step blocks account … | shipped | 0.9275 |
| When a user downloads or saves media (photos, vide… | shipped | 0.7000 |
| App crashes every time a user tries to open/play a… | rejected | 0.6826 |
| Users want the ability to turn on notifications fo… | rejected | 0.6925 |
| Accounts get suspended/labeled with no explanation… | rejected | 0.9450 |

## Grid-search optimum

`{'corroboration': 1.0, 'signal_count': 0.0, 'latency': 0.0, 'roadmap_disconfirmation': 0.0}` -- margin = **0.0000** (1 of 1771 grid points tied for this margin)

| Candidate | Kind | Raw score |
|---|---|---|
| Users can't sign in or join the waitlist because t… | shipped | 1.0000 |
| Users have no way to stop bot/spam accounts from f… | shipped | 1.0000 |
| Follower counts and follower lists don't reflect r… | shipped | 1.0000 |
| A broken CAPTCHA/verification step blocks account … | shipped | 1.0000 |
| When a user downloads or saves media (photos, vide… | shipped | 1.0000 |
| App crashes every time a user tries to open/play a… | rejected | 1.0000 |
| Users want the ability to turn on notifications fo… | rejected | 1.0000 |
| Accounts get suspended/labeled with no explanation… | rejected | 1.0000 |

**Key finding: no weighting of these 4 factors can cleanly separate shipped from rejected.** Even at the best possible grid point, the margin is 0.0000 -- zero or negative, never positive. The blocker is the same one output/rubric_sensitivity.md already flagged from a different angle: *"Accounts get suspended/labeled with no explanation or a slow/absent ap…"* (excluded on scope grounds (SPEC.md §7), not a low score) has raw rubric numbers as strong as or stronger than the weakest shipped gap, *"Follower counts and follower lists don't reflect reality: blocked acco…"*, on every weighting tried. This is a rigorous, quantified version of that same finding: it's not that the hand-picked weights happened to under-rate the excluded candidate -- **no linear combination of these 4 factors can numerically distinguish them**, because the rubric formalizes corroboration/scale/persistence/roadmap-neglect, and the excluded candidate simply scores well on exactly those axes. The exclusion is a scope judgment call that lives outside what this rubric can express, not a gap in how it's weighted.

## Do the optimized weights differ meaningfully?

Per-factor difference (optimized - hand-picked): `{'corroboration': 0.65, 'signal_count': -0.25, 'latency': -0.2, 'roadmap_disconfirmation': -0.2}`. Largest single-factor shift: 0.65.

**Possibly** -- one or more factors shifted by 0.65 or more. Re-scoring below.

## Re-scoring the 5 shipped gaps under the optimized weights (report only)

| Gap | Hand-picked confidence (rounded) | Optimized-weight confidence (rounded) |
|---|---|---|
| Users can't sign in or join the waitlist because t… | 0.95 | 1.0 |
| Users have no way to stop bot/spam accounts from f… | 0.85 | 1.0 |
| Follower counts and follower lists don't reflect r… | 0.65 | 1.0 |
| A broken CAPTCHA/verification step blocks account … | 0.95 | 1.0 |
| When a user downloads or saves media (photos, vide… | 0.7 | 1.0 |

No shipped gap would drop below the 0.5 ship threshold under the optimized weights.

## Limitations (read before citing this anywhere)

- **Small sample, high degrees of freedom.** 8 candidates, 3 free weight parameters -- this grid search can overfit to whichever factor happens to separate these particular 8 rather than validating a generally-better weighting.
- **Circularity risk, named plainly:** the 3 rejected candidates were partly filtered using the ORIGINAL hand-picked rubric and confidence floor in the first place (the falsification pass this rubric was designed alongside). Checking whether a reweighting separates accepted-from-rejected is partly checking agreement with the process that produced the labels, not an independent ground truth. This is exploratory, not a validation study.
- Margin-maximization has no term at all for interpretability or the qualitative meaning of each factor (what corroboration/signal_count/latency/roadmap_disconfirmation *represent*) -- it would happily zero out a factor if that improved separation on these 7 points, which would be a worse rubric even if this narrow objective liked it better.
