# SPEC.md — The Silent Stakeholder

Locked at kickoff. Any change to this file after T+2h needs a team-wide ack in the PR.

## 1. Product

**Product: Bluesky**

- Roadmap source: GitHub issues + milestones from `bluesky-social/social-app`.
- Signal source: uploaded review dataset (data/raw/bluesky_reviews.csv), 8,359 Play Store reviews, app_id 174.

## 2. Normalized data schema

```json
{
  "id": "string — stable, source-prefixed, e.g. 'review-play-00123'",
  "source_type": "review | ticket | github_issue | github_milestone",
  "source_dataset": "string",
  "text": "string",
  "timestamp": "ISO 8601 or null",
  "rating": "number|null",
  "metadata": { }
}
```

## 3. Output contract — the "gap" object

```json
{
  "rank": 1,
  "need": "string in user's terms",
  "confidence": 0.90,
  "confidence_justification": "string with rubric math",
  "verdict": "IGNORED | UNDER-PRIORITIZED | MISUNDERSTOOD",
  "verdict_justification": "string",
  "evidence": [{"id": "...", "excerpt_or_paraphrase": "...", "weight": "primary|corroborating"}],
  "roadmap_refs": [{"id": "...", "relation": "..."}],
  "rejected_alternative_explanations": "string"
}
```

Hard rule: no gap ships with fewer than 2 evidence entries from at least 2 distinct source_types.

## 4. Confidence rubric

confidence = 0.35*corroboration + 0.25*signal_count + 0.20*latency + 0.20*roadmap_disconfirmation

Round to nearest 0.05. A gap under 0.5 does not ship.

## 5. Verdict definitions

- IGNORED: zero adjacent roadmap issues.
- UNDER-PRIORITIZED: issue exists but stale/unlabeled/no milestone.
- MISUNDERSTOOD: issue exists but solves an adjacent, different problem.

## 6. Rejection log

output/rejected_candidates.jsonl — every candidate that didn't survive falsification, with a reason.

## 7. Non-goals

Not a sentiment dashboard. Not frequency ranking alone. One product, both sides.
