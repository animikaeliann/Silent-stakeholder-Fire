# Clustering hyperparameter tuning report

Two clustering methods, swept and compared head-to-head on the SAME joint objective over the full 8359-review corpus, embedded once with all-MiniLM-L6-v2: HDBSCAN (`min_cluster_size` x `min_samples`, 18 settings) and KMeans (`k`, 7 settings). HDBSCAN was the starting recommendation -- it finds its own cluster count and explicitly labels outliers as noise, rather than forcing every review into a cluster the way the original ad-hoc KMeans(k=30) did. It did **not** win this comparison; see below for the real numbers and why KMeans was selected instead.

Joint objective: silhouette and a quick 12-resample Jaccard bootstrap-stability score, each min-max normalized JOINTLY across both methods' settings (so scores are directly comparable), averaged 50/50 -- but ONLY among settings finding >= 5 clusters (a hard eligibility floor, not a soft penalty). Part 2's job is discovering diverse candidate themes (this is how it found CAPTCHA and feed-instability), so a setting that scores well on silhouette+stability by collapsing to one or two giant blobs is not a win, no matter its score -- see Caveats for how HDBSCAN was found to do exactly that, repeatedly, across two grids and an epsilon check.

## Selected method

**`KMeans(k=15)`** -- 15 clusters, 0.0% noise, silhouette=0.042, quick-stability=0.509, joint score=0.449. 7/25 settings across both methods were eligible for selection.

## HDBSCAN sweep (grid 2 -- see Caveats for grid 1 and the epsilon check)

| min_cluster_size | min_samples | n clusters | noise % | silhouette | stability | joint | eligible |
|---|---|---|---|---|---|---|---|
| 8 | None | 2 | 11.8% | 0.087 | 0.479 | 0.505 | no |
| 8 | 5 | 2 | 10.6% | 0.087 | 0.479 | 0.505 | no |
| 8 | 10 | 2 | 13.5% | 0.089 | 0.487 | 0.519 | no |
| 12 | None | 3 | 59.3% | 0.094 | 0.233 | 0.204 | no |
| 12 | 5 | 2 | 10.6% | 0.087 | 0.516 | 0.552 | no |
| 12 | 10 | 3 | 57.4% | 0.091 | 0.219 | 0.180 | no |
| 20 | None | 2 | 79.7% | 0.051 | 0.322 | 0.228 | no |
| 20 | 5 | 3 | 52.1% | 0.087 | 0.249 | 0.211 | no |
| 20 | 10 | 2 | 80.1% | 0.056 | 0.172 | 0.049 | no |
| 30 | None | 3 | 90.2% | 0.272 | 0.390 | 0.777 | no |
| 30 | 5 | 2 | 52.3% | 0.089 | 0.308 | 0.290 | no |
| 30 | 10 | 2 | 80.1% | 0.056 | 0.384 | 0.319 | no |
| 50 | None | 2 | 87.3% | 0.248 | 0.510 | 0.878 | no |
| 50 | 5 | 2 | 72.9% | 0.050 | 0.405 | 0.333 | no |
| 50 | 10 | 4 | 93.7% | 0.243 | 0.282 | 0.577 | no |
| 80 | None | 2 | 88.4% | 0.263 | 0.564 | 0.980 | no |
| 80 | 5 | 4 | 88.6% | 0.176 | 0.303 | 0.465 | no |
| 80 | 10 | 2 | 91.8% | 0.273 | 0.358 | 0.737 | no |

## KMeans sweep

| k | n clusters | silhouette | stability | joint | eligible |
|---|---|---|---|---|---|
| 10 | 10 | 0.033 | 0.493 | 0.409 | yes |
| 15 | 15 | 0.042 | 0.509 | 0.449 **<- selected** | yes |
| 20 | 20 | 0.041 | 0.480 | 0.409 | yes |
| 25 | 25 | 0.043 | 0.441 | 0.365 | yes |
| 30 | 30 | 0.041 | 0.422 | 0.337 | yes |
| 40 | 40 | 0.039 | 0.400 | 0.303 | yes |
| 50 | 50 | 0.037 | 0.377 | 0.270 | yes |

## Caveats

- **HDBSCAN was tried rigorously and rejected on evidence, not preference.** Grid 1 (min_cluster_size in [15, 25, 40, 60, 90, 130]) picked min_cluster_size=130 with a joint score of 0.940 -- but that setting found only 2 clusters at 91.3% noise; silhouette and stability alone don't penalize a coarse, dominant-blob clustering. Re-swept with smaller min_cluster_size values (grid 2, shown above: [8, 12, 20, 30, 50, 80]) after adding the hard >= 5-cluster eligibility floor -- 18/18 of grid 2 STILL didn't clear that floor (max observed: 4 clusters). A follow-up ad-hoc check added `cluster_selection_epsilon` in {0.3, 0.4, 0.5} across 6 more min_cluster_size/min_samples combinations (not tabulated above, run standalone) -- still capped at 2-3 clusters, with the lowest-noise settings (~8-11% noise) having the WORST silhouette (~0.08), i.e. low noise came from lumping nearly everything into two weakly-separated halves, not from finding real structure. This is a genuine property of this corpus's embedding space under a rigorous, density-based definition of "cluster" -- it does not have many small, dense regions; most of the space is diffuse. KMeans's original k=30 result was a forced partition, not evidence of that much real density-based structure.
- KMeans eligibility: 7/7 settings cleared the >= 5-cluster floor (trivially -- KMeans is told k directly).
- No setting in either sweep collapsed to <=1 cluster.
- No setting was simultaneously top-tier on silhouette and bottom-tier on stability in this sweep, so this particular failure mode wasn't directly observed here -- noted for transparency rather than claimed as proof the objective always avoids it.
- The selected setting's silhouette (0.042) is modest in absolute terms, which is normal for sentence-embedding text clustering on a noisy, mixed-topic review corpus.
- Quick stability here uses only 12 resamples to keep both sweeps tractable; Phase 2 (output/bootstrap_stability.md) reruns stability at a much larger N on the winning setting alone.
- `HDBSCAN(algorithm="brute")` is used deliberately, not left at the default: profiling one fit on this exact 8,359x384 embedding matrix showed the default `algorithm="auto"` taking ~46s versus ~2s for `"brute"` with identical cluster output -- this is what made two 18-setting HDBSCAN grids plus the epsilon check tractable at all, even though HDBSCAN ultimately lost.
