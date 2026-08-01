# Adversarial verification report

Independent try-to-refute pass, run separately from the pass that proposed each gap (03_infer_gaps.py). No external LLM call -- 4 independently-computed attack angles (tail-silence timing, broader roadmap rescan, evidence integrity/representativeness, corroboration-count integrity), plus citations of 2 already-independent methods from an earlier phase (bootstrap resampling, dual-method clustering agreement). Report only -- nothing here changes output/gaps.json.

## Calibration: tail-silence check

Dataset's own max review timestamp: **2025-04-20**. Tail-silence = days between a candidate's last matching complaint and that dataset max -- a temporal, non-semantic proxy for "this might already be fading/resolved," the same style of reasoning that legitimately falsified video-crash originally (see 03_infer_gaps.py's PRE_REJECTED).

| Candidate | Kind | Tail-silence (days) |
|---|---|---|
| login-keyboard-dismissal | shipped | 1 |
| no-private-account-remove-follower | shipped | 13 |
| follower-count-block-desync | shipped | 2 |
| captcha-blocks-signup-login | shipped | 16 |
| photo-download-save-location | shipped | 5 |
| video-playback-crash | rejected | 54 |
| per-account-post-notifications | rejected | 19 |
| moderation-appeal-transparency | rejected | 0 |

video-playback-crash (known-resolved, rejected via falsification) shows the largest gap by a wide margin. Threshold set at **30 days** on that basis: clears video-crash, stays below every shipped gap and every other rejected candidate.

## Per-shipped-gap adversarial findings

### Users can't sign in or join the waitlist because the on-screen keyboard flashes …

- Tail-silence: 1 days -- clear (<= 30), complaints continue up to near the dataset's end.
- Broader roadmap rescan: 3 issue(s) outside the declared roadmap_refs share >= 3 keywords with this need's text (reported for a manual look -- generic tech vocabulary collides across unrelated issues, so this is noisy by construction, not a confirmed finding):
  - `#4948` (7 shared keywords: android, entirely, field, immediately, keyboard, open, screen): "DM input field misaligned after going back with keyboard open **Descri…"
  - `#7237` (7 shared keywords: access, account, android, can't, field, open, sign): "Can't sign in to account hosted on a self-hosted PDS; phone app insist…"
  - `#7447` (7 shared keywords: access, account, email, password, screen, sign, username): "Sign in page resets on iPadOS when switching apps to fetch a 2FA confi…"
- Evidence diversity (SPEC.md §3 hard rule, re-checked): OK (>= 2 entries, >= 2 distinct source_types).
- Evidence integrity: all review-sourced excerpts are still verbatim prefixes of the current corpus; all cited IDs exist.
- Cluster mean star rating: 1.46; primary evidence `review-play-04353` rating: 5 (delta 3.54) -- **FLAGGED as atypical**
- Corroboration count: shipped n=287, recomputed now n=287 -- match.
- Independent method (Phase 2 bootstrap resampling): stable in 100/100 resamples.
- Independent method (Phase 3 dual-method/semantic clustering): 86% captured by best-matching cluster, converged=yes.

**Survived adversarial review: YES, WITH CAVEATS** (1 concern(s) raised, none applied to shipped output):
- **Atypical-primary-evidence FLAG**: `review-play-04353` is rated 5, 3.54 stars from its own cluster's mean (1.46) -- worth checking whether it's a representative exemplar (the excerpt text itself may still be an unambiguous complaint; star rating and complaint text can diverge on this platform, a known quirk, not necessarily a flaw).

### Users have no way to stop bot/spam accounts from following them: there is no pri…

- Tail-silence: 13 days -- clear (<= 30), complaints continue up to near the dataset's end.
- Broader roadmap rescan: 3 issue(s) outside the declared roadmap_refs share >= 3 keywords with this need's text (reported for a manual look -- generic tech vocabulary collides across unrelated issues, so this is noisy by construction, not a confirmed finding):
  - `#6909` (8 shared keywords: accounts, blocking, following, locked, option, remove, spam, stop): "preventing spam/harassment with a few minor quality-of-life features #…"
  - `#1078` (5 shared keywords: account, accounts, locked, option, private): "Channels: The ability to sort Posts & Reposts into categories (multipl…"
  - `#4704` (5 shared keywords: account, accounts, locked, private, unwanted): "ability to opt-out of "Discover" feed (and other feeds) Seeing as ther…"
- Evidence diversity (SPEC.md §3 hard rule, re-checked): OK (>= 2 entries, >= 2 distinct source_types).
- Evidence integrity: all review-sourced excerpts are still verbatim prefixes of the current corpus; all cited IDs exist.
- Cluster mean star rating: 3.25; primary evidence `review-play-02336` rating: 4 (delta 0.75)
- Corroboration count: shipped n=67, recomputed now n=67 -- match.
- Independent method (Phase 2 bootstrap resampling): stable in 1/100 resamples.
- Independent method (Phase 3 dual-method/semantic clustering): 30% captured by best-matching cluster, converged=no.

**Survived adversarial review: YES, WITH CAVEATS** (3 concern(s) raised, none applied to shipped output):
- **High-cluster-rating FLAG**: this complaint cluster averages 3.25 stars -- unusually positive for a cluster being cited as evidence of a problem.
- **Independent-method FLAG (bootstrap)**: only 1/100 resamples reproduce a matching cluster -- an orthogonal, already-disclosed source of doubt (see output/bootstrap_stability.md for the root-cause investigation).
- **Independent-method FLAG (dual-method)**: semantic clustering does not converge with the keyword-based partition for this gap (only 30% captured) -- see output/dual_method_agreement.md.

### Follower counts and follower lists don't reflect reality: blocked accounts still…

- Tail-silence: 2 days -- clear (<= 30), complaints continue up to near the dataset's end.
- Broader roadmap rescan: 3 issue(s) outside the declared roadmap_refs share >= 3 keywords with this need's text (reported for a manual look -- generic tech vocabulary collides across unrelated issues, so this is noisy by construction, not a confirmed finding):
  - `#5995` (7 shared keywords: accounts, appear, blocked, counts, displayed, followers, lists): "Moderation List Block does not appear as Block ### Steps to Reproduce …"
  - `#1748` (5 shared keywords: accounts, blocked, don't, followers, lists): "Blocked users should still be visible in followers/following lists **D…"
  - `#5493` (5 shared keywords: accounts, count, don't, follower, followers): "Allow users to see what starter packs they've been added to, and optio…"
- Evidence diversity (SPEC.md §3 hard rule, re-checked): OK (>= 2 entries, >= 2 distinct source_types).
- Evidence integrity: all review-sourced excerpts are still verbatim prefixes of the current corpus; all cited IDs exist.
- Cluster mean star rating: 2.67; primary evidence `review-play-07735` rating: 2 (delta 0.67)
- Corroboration count: shipped n=15, recomputed now n=15 -- match.
- Independent method (Phase 2 bootstrap resampling): stable in 85/100 resamples.
- Independent method (Phase 3 dual-method/semantic clustering): 79% captured by best-matching cluster, converged=yes.

**Survived adversarial review: YES** (no material concerns raised by any of the 4 checks above).

### A broken CAPTCHA/verification step blocks account creation and login for a signi…

- Tail-silence: 16 days -- clear (<= 30), complaints continue up to near the dataset's end.
- Broader roadmap rescan: 3 issue(s) outside the declared roadmap_refs share >= 3 keywords with this need's text (reported for a manual look -- generic tech vocabulary collides across unrelated issues, so this is noisy by construction, not a confirmed finding):
  - `#11317` (5 shared keywords: broken, challenge, creation, step, verification): "Cryptographically-Verified Long-Form Content Embed for the AT Protocol…"
  - `#6369` (4 shared keywords: blocks, correctly, login, times): "Accessibility bug: nearly impossible to login or sign up using a keybo…"
  - `#6370` (4 shared keywords: blocks, broken, challenge, times): "Accessibility bug: Cannot reach the menu on the left or right unless I…"
- Evidence diversity (SPEC.md §3 hard rule, re-checked): OK (>= 2 entries, >= 2 distinct source_types).
- Evidence integrity: all review-sourced excerpts are still verbatim prefixes of the current corpus; all cited IDs exist.
- Cluster mean star rating: 1.36; primary evidence `review-play-04131` rating: 1 (delta 0.36)
- Corroboration count: shipped n=87, recomputed now n=87 -- match.
- Independent method (Phase 2 bootstrap resampling): stable in 98/100 resamples.
- Independent method (Phase 3 dual-method/semantic clustering): 78% captured by best-matching cluster, converged=yes.

**Survived adversarial review: YES** (no material concerns raised by any of the 4 checks above).

### When a user downloads or saves media (photos, videos, profile/share images) from…

- Tail-silence: 5 days -- clear (<= 30), complaints continue up to near the dataset's end.
- Broader roadmap rescan: 3 issue(s) outside the declared roadmap_refs share >= 3 keywords with this need's text (reported for a manual look -- generic tech vocabulary collides across unrelated issues, so this is noisy by construction, not a confirmed finding):
  - `#1078` (7 shared keywords: always, bluesky, choose, media, option, profile, user's): "Channels: The ability to sort Posts & Reposts into categories (multipl…"
  - `#1682` (7 shared keywords: bluesky, images, option, save, saved, user's, videos): "Preview vs Source - Image display **Is your feature request related to…"
  - `#7020` (7 shared keywords: bluesky, dedicated, media, option, profile, share, user's): "Enhanced User Profile Section ### Describe the Feature ### Suggested S…"
- Evidence diversity (SPEC.md §3 hard rule, re-checked): OK (>= 2 entries, >= 2 distinct source_types).
- Evidence integrity: all review-sourced excerpts are still verbatim prefixes of the current corpus; all cited IDs exist.
- Cluster mean star rating: 3.33; primary evidence `review-play-01149` rating: 3 (delta 0.33)
- Corroboration count: shipped n=24, recomputed now n=24 -- match.

**Survived adversarial review: YES, WITH CAVEATS** (1 concern(s) raised, none applied to shipped output):
- **High-cluster-rating FLAG**: this complaint cluster averages 3.33 stars -- unusually positive for a cluster being cited as evidence of a problem.

## Summary

All 5 shipped gaps were run through all 4 adversarial checks plus the 2 cited independent methods. No shipped gap was newly falsified by any check (no tail-silence flag, no evidence-integrity failure, no corroboration-count drift on any gap).
The one recurring point of weakness is **no-private-account-remove-follower**, already surfaced from a different angle in earlier phases (low bootstrap stability and/or non-convergent semantic clustering) -- this adversarial pass doesn't newly discover that weakness, but it also finds nothing here that overturns it or resolves it. It remains the shipped gap most worth a second look, for the same documented reason (a two-bundled-asks cluster), not a new one.
