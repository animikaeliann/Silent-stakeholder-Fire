# Dual-method discovery agreement

Keyword-based discovery (the method that shipped all 4 gaps) and tuned semantic discovery (`kmeans({'k': 15})` from output/clustering_tuning_report.md) run independently against the same 8359-review corpus, then compared -- this run uses semantic clustering as a co-equal primary method, not an after-the-fact validation pass on keyword's output.

## Formal agreement

- **Adjusted Rand Index: 0.0067** (0 = no better than chance, 1 = identical partitions)
- **Normalized Mutual Information: 0.0798**
- Both are computed over a 5-way keyword partition (no-match + 4 shipped gaps) vs. the 15-way semantic partition. A low ARI here is expected and not itself concerning: the two partitions differ enormously in granularity by design (keyword only labels ~4.4% of the corpus with an opinion at all; semantic partitions all of it into 15 groups), so most agreement/disagreement is driven by the ~95.6% of reviews keyword has no opinion on. The per-gap convergence check below is the more interpretable number for "do the two methods agree on the shipped gaps specifically".

## Per-shipped-gap convergence

Converged = the best-matching semantic cluster captures a majority (> 50%) of the gap's own keyword-matched members -- the same majority-membership notion Phase 2's bootstrap match used, for direct comparability. Jaccard is reported alongside as a *distinctiveness* measure (does this cluster consist mostly of this gap, or is the gap a small piece of a much broader cluster) -- it is NOT the convergence criterion, because a gap reliably absorbed into a big general-complaints cluster would otherwise be misread as "not found" purely for the cluster being big, which is a different question from whether the two methods agree the gap's reviews belong together.

| Gap | n (keyword) | Best semantic cluster | % of gap captured | Jaccard | Converged? |
|---|---|---|---|---|---|
| Users can't sign in or join the waitlist beca… | 287 | cluster 7 | 86% | 0.401 | yes |
| Users have no way to stop bot/spam accounts f… | 67 | cluster 1 | 30% | 0.033 | **no** |
| Follower counts and follower lists don't refl… | 14 | cluster 1 | 79% | 0.019 | yes |
| A broken CAPTCHA/verification step blocks acc… | 87 | cluster 9 | 78% | 0.116 | yes |

- **Users can't sign in or join the waitlist because the on-scre…** converged: 86% of its 287 reviews land in one semantic cluster (Jaccard 0.401 -- low because that cluster is much larger than the gap itself, not because the gap is scattered). Consistent with Phase 2's bootstrap stability for this exact gap: 100/100 (100%).
- **Users have no way to stop bot/spam accounts from following t…** did NOT converge: best semantic cluster captures only 30% of its 67 reviews (no majority). Consistent with Phase 2's bootstrap stability for this exact gap: 1/100 (1%) -- both checks independently point to the same root cause (see output/bootstrap_stability.md for the full investigation): this gap bundles two related-but-distinct asks that don't cluster as one tight semantic topic.
- **Follower counts and follower lists don't reflect reality: bl…** converged: 79% of its 14 reviews land in one semantic cluster (Jaccard 0.019 -- low because that cluster is much larger than the gap itself, not because the gap is scattered). Consistent with Phase 2's bootstrap stability for this exact gap: 85/100 (85%).
- **A broken CAPTCHA/verification step blocks account creation a…** converged: 78% of its 87 reviews land in one semantic cluster (Jaccard 0.116 -- low because that cluster is much larger than the gap itself, not because the gap is scattered). Consistent with Phase 2's bootstrap stability for this exact gap: 98/100 (98%).

*(Follower-count-block-desync shows n=14 here, not the 15 in gaps.json: it and no-private-account-remove-follower share exactly 1 review matching both keyword filters -- documented in 03_infer_gaps.py's own alt_explanation for that gap -- and this script's first-match partition assigns it to whichever candidate comes first, unlike gaps.json which counts each gap's matches independently.)*

## Method-specific: semantic finds, keyword doesn't

5 complaint-dominated semantic cluster(s) (mean rating <= 2.5) with no matching keyword filter -- **not merged or promoted to gaps.json**, reported as method-specific for a human judgment call. Cross-check against Phase 1/2: this is expected to be the same set already published in output/semantic_validation.md and output/bootstrap_stability.md (clusters 8/9/14/0/12), not new information -- confirms the two independent runs (this script's fresh embedding pass included) land on the same answer.

| Cluster | Size | Mean rating |
|---|---|---|
| cluster 8 | 680 | 2.10 |
| cluster 9 | 566 | 1.48 |
| cluster 14 | 529 | 2.29 |
| cluster 0 | 231 | 1.93 |
| cluster 12 | 154 | 1.57 |

## Method-specific: keyword finds, semantic doesn't

See the non-convergent gap(s) listed above -- keyword found real, evidence-backed needs (cross-referenced to actual GitHub issues, not just corpus-internal patterns) that the semantic partition doesn't reproduce as a single tight cluster. This is a real limitation of semantic clustering as a *sole* discovery method: a need expressed via multiple differently-worded, sometimes multi-topic reviews can be real and well-evidenced without ever forming one dense embedding region.
