# Latent/second-order candidate synthesis (Phase 2)

Read `output/latent_signals_raw.json` directly and reasoned over it by hand
-- no additional regex/clustering code in this step, per the brief. The bar
applied to every candidate below: **"could a judge have found this by
reading the loudest 20 reviews?"** If yes, discarded, regardless of how the
finding is phrased -- that's a stated complaint, not a latent one.

## Result: 1 candidate carried forward, thin and borderline; several
## considered and explicitly rejected below

This is not a strong positive result, and it's reported that way on
purpose. Detector 1 (workaround language) and Detector 2 (implicit
comparison) surfaced 28 and 55 raw matches respectively; the large
majority of both are directly-stated complaints or feature requests that
simply use workaround/comparison language as their *phrasing* -- they
don't conceal anything. Detectors 3 and 4 (silent-churn divergence,
cross-cluster correlation) returned clean negative results after a real
methodological fix to Detector 4 (see below) -- also reported honestly as
negative findings, not massaged into something positive.

## Candidate carried to Phase 3: implicit expectation of persistent read-state

**Synthesized need (in the user's terms, not any one reviewer's):**
Bluesky has no persistent "where you left off" state anywhere in the
app -- not in the main feed, not in the following feed, not in
notifications -- so every time a user reopens the app, background-checks
it, or wants a refresh, they land back at the newest content with no way
to resume where they stopped reading. Users experience this as three
separately-phrased, seemingly unrelated quality-of-life complaints
(notifications don't refresh without a restart; the following feed
doesn't remember your last-read post; the main feed jumps to the newest
post on every refresh instead of preserving reading position) rather than
recognizing it as one underlying architectural gap, because no single
symptom, by itself, looks like it's connected to the other two.

**Evidence (4 reviews, span 2023-09-02 to 2025-04-14 -- 19 months, never
clustered together before this pass):**
- `review-play-00687` (2023-09, ★4): "Is it possible to have your
  following feed start on the last post you read? I find myself having to
  scroll back for last post each time I open... (like other lesser apps)"
- `review-play-01857` (2024-10, ★3): "I have to restart the app whenever I
  want to refresh my notifications. It's not a smooth experience trying
  to keep up to date, unlike Twitter."
- `review-play-06630` (2025-01, ★3): "(unlike Twitter) it doesn't remember
  where you were. Every time I open it it goes straight to the newest
  stuff... It really needs to remember where you left off"
- `review-play-08298` (2025-04, ★2): "let me read my timeline in a
  chronological order from my last read post to the newest post each time
  I refresh"

**Detector(s):** Detector 1 (workaround language: "have to restart" /
"each time i" on 01857, 00687, 08298) and Detector 2 (implicit-standard
via comparison: "unlike Twitter" on 01857, 06630).

**Honest answer to "could a judge find this from one review": genuinely
close, disclosed as such, not asserted with full confidence.** Each
*individual* symptom is, on its own, a plainly-stated complaint -- a judge
reading `review-play-06630` alone would immediately understand "this
reviewer wants the app to remember their scroll position," no inference
required. What is NOT stated anywhere is the connection between these
three symptoms as one underlying gap: nobody names "notifications,"
"following feed," and "main feed" together, and each review individually
reads as an unrelated, minor, easily-dismissed nitpick -- which is
presumably exactly why, despite spanning 19 months, this pattern was never
picked up by the original keyword-clustering pass (no shared keyword
connects "restart to refresh notifications" with "remembers where you
were"). A judge skimming even a generous "loudest 20 reviews" sample
(which would be dominated by the volume-heavy, well-corroborated themes:
keyboard dismissal, CAPTCHA, moderation/political content, crashes) would
almost certainly never encounter enough instances of this thin, scattered
pattern to notice the cross-cutting connection. That said: I want to name
the tension plainly rather than paper over it. This synthesis is closer to
"three related-but-separately-obvious complaints given one unifying label"
than to a signal that was truly invisible until aggregated -- a reasonable
reader could look at the same 4 reviews and conclude I'm building a
narrative across otherwise-ordinary feature requests, not discovering
something hidden. I'm carrying it to Phase 3 rather than deciding that
argument myself, because Phase 3's rubric (corroboration count
especially) will likely settle it more objectively than my own judgment
call here: with n=4, corroboration = 4/15 = 0.27, which is low enough that
the existing rubric may reject it on the numbers regardless of how the
latent-ness question is resolved.

## Considered and explicitly rejected (fails the "one review" test)

- **Bookmark/save-post feature** (`review-play-00909`, `-01966`, `-02963`,
  `-05130`, `-05908` -- 5+ reviews): every single one directly and
  plainly states "I wish I could save/bookmark posts." A judge reading
  ANY one of these (especially `-05908`: "I would literally give my left
  kidney for a bookmark option") gets the complete ask immediately.
  Rejected: directly stated, just well-corroborated and apparently not
  picked up by the original 4-gap pass for unrelated reasons (not a
  second-order signal).
- **No edit button** (`review-play-02030`, `-04436`, `-07149`): same
  reasoning -- directly, repeatedly, explicitly stated.
- **Photo/image save-location** (saves to camera roll/DCIM instead of a
  dedicated folder -- 29 reviews found via a broader corpus sweep,
  `review-play-00543` through `-08306`, spanning the full 2023-2025
  window): this is a striking finding in its own right -- 29 independent,
  well-corroborated, plainly-worded complaints ("Please, for the love of
  God, change the folder..."), never surfaced by the original
  keyword-clustering pass. But it fails this phase's specific test
  decisively: every one of the 29 reviews states the exact ask in plain
  language. This is a real, apparently-missed STATED gap, not a latent
  one -- worth someone's attention separately, but out of scope for what
  this phase is chartered to find, and forcing it through here would be
  exactly the "no matter how you phrase it" mistake the brief warns
  against.
- **Muted-words workaround failure** (`review-play-01423`, `-05474`,
  `-07214`, `-07771`): each is its own directly-stated complaint (a
  specific muting bug, a direct "add a No Politics button" request, a
  content-filter failure, a performance complaint) -- they don't converge
  into one coherent hidden pattern on inspection; they just happen to all
  mention "muted."
- **Session/re-login frustration** (`review-play-07213`, `-07692` -- only
  2 reviews): directly stated ("I shouldn't have to keep putting in my
  password every 24 hours"), and too thin regardless (n=2).
- **General crash/restart-for-instability** (`review-play-00535`,
  `-02266`, `-06431`, `-07381`, `-07691`, `-08316`): these are generic
  "the app crashes and I have to restart it" complaints -- ordinary
  bugginess, about as directly stated as a complaint gets. Not a distinct
  latent pattern once separated from the notification/feed-position-
  specific subset above.

## Detector 3 (silent-churn divergence): 0 themes flagged, honest negative

Checked 10 themes (4 shipped gaps, 3 rejected candidates, 3 new candidate
themes from Detector 1/2 exploration: muted-words-workaround,
manual-refresh-restart-workaround, photo-folder-workaround). None showed
the target signature (explicit complaint volume declining while
churn-adjacent language volume, co-occurring with the same theme, rises).
Where there was enough data to check at all (login-keyboard-dismissal,
n_churn=25; captcha-blocks-signup-login, n_churn=10), complaints were
either still rising (login-keyboard) or declining in step with churn
rather than diverging from it (captcha) -- consistent with, not
contradicting, the earlier adversarial-verification finding that both
gaps are genuinely still live, not silently abandoned. Most other themes
had too few churn-co-occurring reviews (0-2) to test at all. This is a
clean, disclosed negative result, not a detector failure.

## Detector 4 (cross-cluster time-correlation): 0 pairs, after a real fix

The first real run flagged 13 theme pairs at |r| >= 0.6 using raw monthly
counts. Investigating why (rather than trusting the number) found total
review volume itself spikes ~10x in 2024-11 (a real, well-known event --
2,546 reviews that month vs. a typical 40-500) -- every theme rides that
same wave, so virtually any two themes correlate on raw counts regardless
of any real relationship. Fixed by correlating each theme's *share* of
that month's total volume instead of raw counts (see
`scripts/16_latent_signal_mining.py`'s `monthly_share_vector`, and the
regression test added for this exact bug). After the fix: 0 pairs clear
the same 0.6 threshold. The closest near-miss, kept in
`output/latent_signals_raw.json` for transparency:
`follower-count-block-desync` <-> `video-playback-crash`, r=+0.595 (n=15,
n=32) -- below threshold, and with samples this small a single
coincidentally-overlapping month can move the correlation coefficient
substantially, so this is not treated as a finding.

## Summary

1 of ~10+ raw candidate patterns is carried to Phase 3, and it's disclosed
as borderline rather than confidently latent. Everything else considered
either fails the "one review" test decisively (several well-corroborated,
directly-stated complaints that the original pipeline happened not to
surface -- a different, real, but out-of-scope finding) or returned a
clean, methodologically-checked negative (Detectors 3 and 4).
