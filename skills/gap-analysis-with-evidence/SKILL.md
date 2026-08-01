---
name: gap-analysis-with-evidence
description: Use when analyzing user feedback (reviews, tickets, support transcripts, survey text) against a roadmap or backlog to find needs that are being ignored, under-prioritized, or misunderstood. Also use for any task that requires turning a pile of unstructured signal into a small set of ranked, evidence-backed findings with a calibrated, auditable confidence score per finding — and for adversarially fact-checking findings before they ship, so a weak conclusion is caught before a stakeholder sees it rather than during a defense of it.
---

# Gap analysis with evidence

A six-stage method for turning unstructured feedback into a small number of
defensible findings, each traceable back to specific evidence and scored by
a rubric a reader can re-derive by hand. Built and refined against a real
run: 8,359 app reviews cross-referenced against ~1,800 GitHub issues/
milestones, four findings shipped, three rejected, all disclosed. The
concrete rubric and schema below are that run's actual `SPEC.md` contract —
reuse its shape, not its literal weights, for a new domain.

## The six stages, in order

### 1. Normalize to a schema

Before anything else, put every source (reviews, tickets, roadmap items,
support logs) into one common shape. Minimum viable fields: a stable
source-prefixed `id`, `source_type`, raw `text`, a `timestamp` (or `null`,
never a guess), and a `metadata` bag for source-specific fields (rating,
labels, milestone, whatever else survives). Log anything filtered or
dropped, with a reason, to a side file — don't just discard it silently.
Reference: this project's schema is `SPEC.md` §2; the log convention is
`logs/filtered.jsonl`, append-mode, one JSON object per dropped/flagged
record.

**Why this stage matters:** every later stage assumes one uniform shape.
Skipping it means every downstream script re-implements its own parsing,
and inconsistencies (a review with `rating: null` vs `rating: 0`) become
silent bugs three stages later instead of one visible decision now.

### 2. Cluster / group the signal

Group the normalized signal into candidate "needs" — the specific things
users are asking for or complaining about. Two complementary approaches,
not one:

- **Keyword/rule-based grouping**: a human reads a sample of the corpus,
  identifies recurring needs, and writes an explicit predicate per need
  (e.g. `"keyboard" in text and any_has(text, ["log", "sign", "password"])`).
  Transparent and auditable — a reviewer can see exactly why a given
  record matched — but only as good as the human's initial read.
- **Semantic/embedding-based grouping** (independent validation, not a
  replacement): embed the corpus, cluster it (HDBSCAN or KMeans — tune
  both under a joint objective, e.g. silhouette + bootstrap stability, and
  let the data pick the winner rather than assuming one clustering
  algorithm's default settings are correct), and check whether the
  keyword-based candidates line up with cluster boundaries found without
  any hand-authored predicate.

Report agreement between the two methods formally (Adjusted Rand Index /
Normalized Mutual Information / majority-capture fraction — pick whichever
answers "do these two independent methods agree," and know that raw
Jaccard similarity alone can *wrongly* penalize a real, valid finding for
being a small piece of a much larger natural cluster — capture fraction
usually answers the intended question better). Don't merge or promote
across methods; report where they agree and where they don't, and say why
if you can find out.

### 3. Cross-reference against the roadmap/backlog

For each candidate need, search the roadmap/backlog for anything already
adjacent to it. This is what turns "users are unhappy about X" into an
actionable verdict:

- **Nothing adjacent found** → the need is being flat-out ignored.
- **Something adjacent exists but is stale, unlabeled, or has no
  milestone** → it's known but under-prioritized.
- **Something adjacent exists but solves a different, narrower problem**
  → the team may have misunderstood the actual need.

Score how badly the roadmap fails to address the need on a continuous
scale, not just a three-way label — e.g. this project's
`roadmap_disconfirmation()` gives a closed-and-not-planned issue 0.9, a
stale unmilestoned issue 0.8, a never-milestoned-but-old issue 0.65, an
unlabeled issue 0.55, a freshly-opened unmilestoned issue 0.45, and an
actively-scheduled issue only 0.15 — auditable per-issue reasons, not a
black-box number.

### 4. Score with an explicit, auditable rubric

Combine however many factors matter (this project used 4: corroboration
count, absolute signal volume, how long the issue has persisted, and how
much the roadmap fails to address it) into one confidence score via a
**linear, hand-inspectable formula** — not a black box, not a neural net.
Concretely:

```
confidence = w1*factor1 + w2*factor2 + w3*factor3 + w4*factor4   (weights sum to 1.0)
```

Round to a coarse step (this project: nearest 0.05) so the number doesn't
imply false precision, and set an explicit ship/no-ship threshold (this
project: confidence < 0.5 does not ship). Require a minimum evidentiary
bar independent of the score — this project's hard rule: no finding ships
with fewer than 2 evidence entries from at least 2 distinct source types.
Write the rubric math into the finding itself (`confidence_justification`)
so a reader can redo the arithmetic by hand from the stated factor values.

If you want to check whether the hand-picked weights are actually doing
useful work, grid-search the weight simplex for the weighting that best
separates accepted from rejected candidates by margin — but disclose the
circularity plainly if the rejected set was partly produced using these
same weights in the first place (checking self-agreement is not
independent validation), and treat the result as exploratory, never as
something to silently substitute in.

### 5. Adversarially verify

Before anything ships, run a **separate pass** whose only job is to argue
*against* each candidate finding, using the same evidence pool. This must
be a genuinely different computation from the one that proposed the
finding — re-running the same check with the same logic just confirms
itself. Concrete, reusable attack angles (none of these require an
external LLM call — plain deterministic checks work and are easier to
audit):

- **Self-resolution language**: has anyone in the evidence pool said this
  was already fixed/resolved? Both a literal keyword pass and a semantic
  (embedding-similarity-to-exemplar) pass catch different phrasings —
  calibrate any embedding threshold against known regression cases, and
  watch for negation-blindness (embeddings often score "this got fixed"
  and "this is still broken" as similar, since they share vocabulary;
  mitigate with an explicit negation-cue lexical filter, and always
  manually read what survives the filter before trusting a count).
- **Temporal/volume decay**: does the complaint volume for this cluster
  go quiet near the end of the data window, independent of what anyone's
  text says? A real, non-semantic proxy for "this may already be fading" —
  but calibrate it against a known-resolved case first, since a dataset's
  own right-censored ending can look like decay even for issues that
  never got fixed.
- **Broader coverage rescan**: search the *entire* roadmap/backlog for
  keyword overlap with the need, not just the specific items a human
  curator hand-picked — catches "already covered, but the citation missed
  it." This is inherently noisy (generic vocabulary collides across
  unrelated items) — report it as "worth a manual look," never as a
  confirmed finding by itself.
- **Evidence integrity**: re-verify every cited evidence ID still exists
  in the current corpus and that excerpts are still faithful to the
  source text (catches drift, not just fabrication). Also check whether
  the "primary" piece of evidence is representative of its own cluster
  (e.g. a 5-star review being cited as complaint evidence is a real,
  disclosable anomaly worth a footnote, even if the excerpt text itself is
  unambiguous).
- **Recompute, don't trust cached numbers**: re-derive corroboration
  counts directly from the current data rather than trusting whatever a
  prior pass wrote down, to catch silent drift between passes.

Report every real concern plainly, even when it doesn't change the
verdict — "no change, confirms robustness" is a legitimate and valuable
finding, not a null result to bury. Any concern that *would* change a
shipped finding goes back to a human for an explicit decision; this stage
never silently rewrites what already shipped.

### 6. Ship only survivors, with evidence IDs

The final output is a small, ranked list of findings that survived stages
3–5, each carrying: the need in the user's own words, the confidence
score with its rubric arithmetic shown, a verdict (ignored /
under-prioritized / misunderstood, or your domain's equivalent), the
specific evidence entries (with stable IDs, so anyone can go look), and an
explicit accounting of alternative explanations considered and rejected.
Keep a rejection log for everything that *didn't* survive, with the
specific reason — a falsification-based rejection ("this was already
fixed") is a different kind of finding than a scope-based exclusion
("this is out of bounds per the project's own non-goals"), and the two
should never be described using the same language in a report.

## Applying this to a new domain

The stages, the rubric-must-be-linear-and-auditable rule, and the
try-to-refute pattern in stage 5 transfer directly to any "find what's
being missed" task: support-ticket triage against a product roadmap,
incident postmortems against a known-issues list, research-paper claims
against prior work. What changes per domain is just: what counts as a
source record, what the roadmap/backlog equivalent is, and which 3-5
factors belong in the rubric. Keep the factor count small (this project
used 4) — more factors buys diminishing rigor and costs auditability.
