# End-to-end integration verification

Run manually against a live backend (no browser tooling available in this
session — see caveat at the bottom).

## 1. Backend starts and serves real data

```
uvicorn backend.app:app --port 8000
```

Confirmed live:

| Check | Result |
|---|---|
| `GET /health` | `200`, `{"status":"ok","gaps_loaded":3,"rejected_loaded":3}` |
| `GET /gaps` | `200`, JSON array of 3 gap objects |
| `GET /gaps/1` / `/2` / `/3` | `200`, each returns the matching gap |
| `GET /gaps/999` | `404` |
| `GET /rejected` | `200`, JSON array of 3 rejected-candidate objects |
| CORS | `Access-Control-Allow-Origin: *` present on responses (verified with `curl -H "Origin: null"`, matching a `file://`-opened frontend) |

## 2. Frontend field-for-field match against the live response

`frontend/index.html` was checked against the actual `/gaps` and `/rejected`
payloads above (not just the schema on paper):

- `gap.rank`, `gap.need`, `gap.verdict`, `gap.confidence`,
  `gap.verdict_justification`, `gap.confidence_justification`,
  `gap.evidence[].{id,excerpt_or_paraphrase,weight}`,
  `gap.roadmap_refs[].{id,relation}`, `gap.rejected_alternative_explanations`
  — every key the JS reads exists in the live response with the expected type.
- `rejected[].{need,reason,supporting_evidence_ids}` — same check for `/rejected`.
- Verdict values seen in the data (`UNDER-PRIORITIZED`) have a matching CSS
  class (`.verdict-UNDER-PRIORITIZED`); `IGNORED` and `MISUNDERSTOOD` classes
  are also defined and would render correctly if a future run produces them.
- `API_BASE` in the frontend (`http://127.0.0.1:8000`) matches the port the
  backend is started on in this doc and in the README. Deliberately `127.0.0.1`,
  not `localhost`: on at least one dev machine `localhost` resolved to `::1`
  first, which collided with an unrelated service already bound to `[::]:8000`
  (in this case Docker Desktop's backend) and returned its `{"message":
  "Unauthorized"}` instead of ever reaching our app. `curl http://127.0.0.1:8000/...`
  always reaches this API regardless of what else is squatting on the IPv6 side
  of the port.

## 3. Static checks on the frontend itself

- Embedded `<script>` block: brace/paren/bracket counts balanced (55/55,
  74/74, 5/5) — no obvious syntax break.
- Full HTML parsed with Python's `html.parser` with no errors raised.

## Caveat

No browser automation tool was available in this session (Claude in Chrome
was declined). The checks above verify the contract the frontend depends on
(API shape, CORS, JS structural validity) but do not confirm actual pixel
rendering. **Before presenting live, open `frontend/index.html` in an actual
browser once with the backend running** and eyeball: card layout, confidence
bar fill, expand/collapse of the evidence section, and that the rejected-
candidates section renders below the gaps.
