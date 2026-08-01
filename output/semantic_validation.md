# Semantic clustering validation

Independent check using local sentence embeddings (all-MiniLM-L6-v2, no external API), run against all 8359 normalized reviews. This does not replace or modify 03_infer_gaps.py's keyword-based clustering -- it's a second opinion.

## Part 1 — semantic cluster size vs keyword cluster size, per shipped gap

| Gap | Keyword n | Semantic n (sim >= 0.45) | Overlap | Consistent? |
|---|---|---|---|---|
| Users can't sign in or join the waitlist because t… | 287 | 934 | 285 | DIVERGES |
| Users have no way to stop bot/spam accounts from f… | 67 | 2591 | 65 | DIVERGES |
| Follower counts and follower lists don't reflect r… | 15 | 535 | 15 | DIVERGES |
| A broken CAPTCHA/verification step blocks account … | 87 | 658 | 84 | DIVERGES |

**login-keyboard-dismissal**: semantic pass found 649 reviews above threshold that keyword matching missed. Sample: Definitely better than all the other social media apps and platforms out there. It's still a bit bugged though. It regularly happens that an | It simply does not work. It continuously closes, not giving time even to sign in. | So the app won't even let me sign up! Like what the hell!!

**no-private-account-remove-follower**: semantic pass found 2526 reviews above threshold that keyword matching missed. Sample: It's literally an amazing alternative to ykw!! I can block people and stuff. Yay!! | App feels really good. Content is lovely. Not toxic at all. Everything feels nice | Advertised as a bot free social media site. Within 1 hour of installing and messaging or following no one, I received no fewer than 6 notifi

**follower-count-block-desync**: semantic pass found 520 reviews above threshold that keyword matching missed. Sample: Super nice platform, especially for artist and people into specific fandoms! Unlike twitter there's not an unmanageable amount of bots and I | It's great. It's missing a handful of features, like voice posts, private accounts, proper bookmarked posts and the sort, but it has plenty  | Just needs a notification option. Especially seeing as so many people are migrating from another social media platform that has one. Otherwi

**captcha-blocks-signup-login**: semantic pass found 574 reviews above threshold that keyword matching missed. Sample: I can't even use it | It simply does not work. It continuously closes, not giving time even to sign in. | So the app won't even let me sign up! Like what the hell!!

## Part 2 — unsupervised clustering for candidates keyword matching never targeted

5 cluster(s) found that are large (>= 30 reviews), complaint-dominated (mean rating <= 2.5), and mostly NOT covered by any existing keyword filter (<= 35% overlap). Each is reported below with sample reviews for a human judgment call -- **none of these are added to gaps.json**; they have not been through roadmap cross-checking, confidence scoring, or falsification.

### Cluster 8 — 680 reviews, mean rating 2.1, 4% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00007` (rating=1): Keeps crashing on launch on pixel 7
- `review-play-00013` (rating=2): Not opening
- `review-play-00019` (rating=1): Not working
- `review-play-00038` (rating=1): It doesn't install.. Reads to 100% and just freezes tried it twice and all same
- `review-play-00049` (rating=1): The splash screen time takes too long to load and lags a lot .

### Cluster 9 — 566 reviews, mean rating 1.5, 21% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00047` (rating=1): Why is the user name not working this not cool
- `review-play-00053` (rating=1): Have downloaded the app but I would have to uninstall it because when I tried to sign up an error occurs saying my email is invalid
- `review-play-00095` (rating=1): Is this app is only available for verified accounts ?
- `review-play-00123` (rating=2): Having difficulties creating the new account
- `review-play-00126` (rating=1): Second attempt of scam and same owner of jawaeye. Please don't waisted your time and money.

### Cluster 14 — 529 reviews, mean rating 2.3, 2% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00078` (rating=1): What a way for democrats to ban free speech and spread propaganda 😂😂😂
- `review-play-00156` (rating=1): A liberal echo chamber
- `review-play-00189` (rating=1): UGH, tweet clone: skeets for the confused. AVOID this tainted platform at all costs!
- `review-play-00211` (rating=1): Read the TOS. The TOS is absolutely outrageous.
- `review-play-00260` (rating=1): Absolute garbage. EXTREMELY buggy. Posts disappear. And will run into legal issues later since a company sold themselves to another person and then they created

### Cluster 0 — 231 reviews, mean rating 1.9, 0% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00002` (rating=3): Hi anyone has invite code?
- `review-play-00006` (rating=4): Someone please share me an invitation code. I am eagerly waiting to use and test the app
- `review-play-00010` (rating=5): Fantastic just like old twitter, got some invite codes I'll give to friends
- `review-play-00014` (rating=2): It requires Sign up code
- `review-play-00015` (rating=2): I don't have any experience. How exactly do we get the invitation code?

### Cluster 12 — 154 reviews, mean rating 1.6, 22% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00008` (rating=1): Not yet available, requires waitlist
- `review-play-00020` (rating=1): OK, it finally arrives on Android. So what? The "we'll be in touch shortly" message I got when I joined the waitlist in February didn't specify how they define 
- `review-play-00032` (rating=4): Not really felt the vibes of it. Currently on waitlist.
- `review-play-00046` (rating=2): Why release for all on Android if there js a waitlist. Just to occupy space on your phone. Or just to show more downloads?
- `review-play-00070` (rating=2): When I try to enter my email for the waiting list the keyboard keeps disappearing

## Synthesis — reading the 5 flagged clusters (human judgment pass, re-run after re-tuning k)

This run uses the tuned KMeans(k=15) from scripts/10_tune_clustering.py (replacing the earlier
ad-hoc k=30). Reading all 5 flagged clusters in full, not just the 5-sample excerpts above:

**All 5 map onto themes already considered, none are new this time:**
- Cluster 8 (680 reviews) and Cluster 9 (566 reviews) are both flavors of the "app fails before I
  can use it" theme (crashes on launch, won't install, sign-up throws an invalid-email error) --
  the same theme found as 4 separate smaller clusters under k=30, now merged into 2 bigger ones.
  Still not roadmap-checked or shipped as a gap; still worth a look if a 5th gap slot opens up.
- Cluster 14 (529 reviews) mixes the partisan "echo chamber" sentiment already excluded on
  SPEC.md §7 non-goal grounds with generic bug complaints and TOS gripes -- coarser and messier
  than the k=30 pass's cleaner separation, but the same underlying exclusion still applies to the
  political-sentiment portion.
- Clusters 0 (231) and 12 (154) are both the same historical invite-code/waitlist theme already
  found, dated (April 2023), and excluded as resolved history in the original analysis.

**A real cost of re-tuning, not just a benefit:** the k=30 pass's two genuinely novel findings were
CAPTCHA (since cross-checked, falsified, and shipped as gap #2) and a feed/scroll-position-
instability cluster (~166 reviews: "refreshes itself and forces me back to the top," "switches
tabs side to side, far too sensitive"). CAPTCHA is correctly absent from this list now -- it's a
known theme (part of `known_filters()` via `infer.CANDIDATES`), not a gap in coverage. But the
feed/scroll-instability theme does **not** reappear as its own cluster under k=15 -- it's likely
diluted into the two larger, less specific clusters above rather than standing out. This is the
tradeoff the tuning report already names: k=15 is the more *defensible* setting (jointly optimizing
silhouette and bootstrap stability, per output/clustering_tuning_report.md), but coarser k trades
away some fine-grained discovery power that a looser, ad-hoc k=30 happened to provide. Worth
knowing before claiming the tuned method is strictly better in every respect -- it's better
*justified*, not universally higher-resolution.

**Part 1 caveat still holds:** the "DIVERGES" numbers for `no-private-account-remove-follower`
(2,591→2,526 reviews) and `follower-count-block-desync` are still mostly method noise from the
same too-loose 0.45 threshold, not real missed evidence -- spot-checked again this run (e.g. "App
feels really good... not toxic at all" is generic praise, not private-account corroboration). See
the original synthesis (git history) for the full spot-check; the conclusion is unchanged by
re-tuning k, since Part 1 never used KMeans at all.
