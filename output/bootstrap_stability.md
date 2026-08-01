# Bootstrap stability analysis

100 bootstrap resamples (with replacement, same size as the 8359-review corpus each time) of the tuned clustering method (`kmeans({'k': 15})`, selected in output/clustering_tuning_report.md -- see that report for why KMeans, not the initially-recommended HDBSCAN, ended up selected). Embeddings were computed once and reused across every resample -- only which rows are drawn changes, not the embeddings themselves. Total run time: 139s (1.39s/resample).

A resample counts as a **match** for a target if a majority (> 50%) of that target's originally-matched reviews that are in-bag for this resample land in the same resample cluster (not noise). Stability score = fraction of resamples that match.

## Shipped-gap stability

| Gap | n reviews | Stable in | Avg. overlap fraction | Avg. centroid sim (on match) |
|---|---|---|---|---|
| Users can't sign in or join the waitlist because the on… | 287 | 100/100 (100%) | 0.91 | 0.972 |
| Users have no way to stop bot/spam accounts from follow… | 67 | 1/100 (1%) | 0.33 | 0.859 |
| Follower counts and follower lists don't reflect realit… | 15 | 85/100 (85%) | 0.69 | 0.778 |
| A broken CAPTCHA/verification step blocks account creat… | 87 | 98/100 (98%) | 0.74 | 0.796 |

**Weakest shipped gap by this metric:** Users have no way to stop bot/spam accounts from following them: there… -- stable in 1/100 resamples. This is below 70% and worth a second look before the defense.

**Investigated why, not just reported the number.** Checked which full-data KMeans(15) clusters
this gap's 67 reviews actually land in: they're split across 8 different clusters, with the
largest holding only 20/67 (30%) -- never a majority, which is exactly why the bootstrap match
criterion (> 50%) almost never fires, in every resample, not just as noise. Root cause: this
gap's keyword filter bundles two related-but-distinct asks -- "private/locked account" (50
reviews) and "remove a follower without blocking" (16 reviews) -- and only 1 review mentions
both together. Many of the privacy-account reviews are broad multi-feature wishlists ("1.
Bookmark/save 2. Private account 3. Moment feature...", "Wanting features like: audio files,
voice notes, bookmarks, drafts, post scheduling, group [DM]...") that embed near *other*
multi-feature wishlist reviews discussing unrelated asks, not near each other -- unlike the
narrow, specific, repeatable phrasing of the login-keyboard bug ("keyboard flashes and
disappears") or CAPTCHA ("captcha fails/doesn't work"), which is why those two are the most
bootstrap-stable.

**This does not mean the gap is weak on the confidence rubric** -- corroboration, signal count,
latency, and roadmap disconfirmation don't depend on cluster tightness, and the 67 reviews, the
1-review keyword-filter overlap, and the 2 exact-match GitHub issues (#1155, #1160) are all real
and independently checkable regardless of this result. What low stability actually reveals: this
gap is a bundle of two adjacent feature requests rather than one narrowly-worded complaint, so it
doesn't form as tight a semantic cluster as the other three. Worth being ready to explain exactly
this way in the defense if asked "how confident are you in gap #3 specifically" -- the honest
answer is "very, on the evidence; less so as a single semantic topic, and here's why."

## Bootstrap-discovered candidates (not yet in pipeline)

These clusters appeared in the full-data tuned clustering, did not closely match any shipped gap or already-rejected candidate, and are complaint-dominated (mean rating <= 2.5 -- 9 other large cluster(s) were excluded here for being majority-praise instead, same floor 06_semantic_clustering_check.py uses and checked here explicitly rather than assumed). Reported with their bootstrap stability for context -- **none are added to gaps.json**; they have not been roadmap-cross-checked, scored, or falsification-tested.

| Cluster | Size | Mean rating | Stable in |
|---|---|---|---|
| novel-cluster-8 | 680 | 2.10 | 95/100 (95%) |
| novel-cluster-9 | 566 | 1.48 | 99/100 (99%) |
| novel-cluster-14 | 529 | 2.29 | 100/100 (100%) |
| novel-cluster-0 | 231 | 1.93 | 100/100 (100%) |
| novel-cluster-12 | 154 | 1.57 | 72/100 (72%) |

## Methodology notes

- Bootstrap resampling with replacement means ~63% of the corpus is "in-bag" for any given resample (the standard 1-1/e rate for n draws from a pool of n); the match criterion is evaluated only against a target's in-bag members for that resample, not its full original set.
- This measures cluster-level reproducibility under resampling, which is a different question from the confidence rubric (corroboration/scale/persistence/roadmap-neglect) -- a gap can score high on one and be unmeasured by the other. They're complementary, not substitutes.
- Novel-cluster detection caps at the 5 largest unmatched full-data clusters to keep the bootstrap run tractable; smaller unmatched clusters exist but weren't tracked individually here.