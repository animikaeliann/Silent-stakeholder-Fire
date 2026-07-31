# Semantic clustering validation

Independent check using local sentence embeddings (all-MiniLM-L6-v2, no external API), run against all 8359 normalized reviews. This does not replace or modify 03_infer_gaps.py's keyword-based clustering -- it's a second opinion.

## Part 1 — semantic cluster size vs keyword cluster size, per shipped gap

| Gap | Keyword n | Semantic n (sim >= 0.45) | Overlap | Consistent? |
|---|---|---|---|---|
| Users can't sign in or join the waitlist because t… | 287 | 934 | 285 | DIVERGES |
| Users have no way to stop bot/spam accounts from f… | 67 | 2591 | 65 | DIVERGES |
| Follower counts and follower lists don't reflect r… | 15 | 535 | 15 | DIVERGES |

**login-keyboard-dismissal**: semantic pass found 649 reviews above threshold that keyword matching missed. Sample: The app still won't let me sign in after a month. I've even reported to bug. Nothing. | Tried to make a account could not get a proper username so I gave up so your app sucks | there is a problem with logging in...it won't let you select or type anything

**no-private-account-remove-follower**: semantic pass found 2526 reviews above threshold that keyword matching missed. Sample: Well, this app is a such breath of fresh air, especially compared to Elon's hellsite I do have a few suggestions for improvement though :3 - | The app still won't let me sign in after a month. I've even reported to bug. Nothing. | Bluesky was supposed to be a complete copy (90 to 100% copy) of Twitter before becoming a complete reiteration of what Twitter is supposed t

**follower-count-block-desync**: semantic pass found 520 reviews above threshold that keyword matching missed. Sample: Not having OF bots following you daily is nice. | This app is amazing, but one of the only downsides it has compared to Twitter is that it doesn't send you a mobile notification when someone | Can you add a notification feature for this app where you get a notification for when a profile you follow posts Something?

**Caveat on the "DIVERGES" numbers above (read the samples, not just the counts):**
having spot-checked the actual extra reviews rather than trusting the raw sizes,
most of this expansion is a **false positive of a too-loose 0.45 cosine
threshold**, not real missed evidence:

- `no-private-account-remove-follower`'s 2,591-review semantic cluster is ~31%
  of the *entire corpus* -- its samples ("breath of fresh air compared to
  Elon's hellsite," "app still won't let me sign in," "supposed to be a copy of
  Twitter") are generic negative/comparative sentiment, not corroboration for
  private-account/remove-follower specifically. Same story for
  `follower-count-block-desync`'s samples (a bot-follower aside, an unrelated
  notification request). These two divergences should be read as **method
  noise, not evidence the keyword cluster undercounted**.
- `login-keyboard-dismissal` is the one exception worth taking seriously: one
  of its three samples -- "there is a problem with logging in...it won't let
  you select or type anything" -- is a real instance of the same symptom the
  keyword filter missed only because it doesn't contain the literal word
  "keyboard." This suggests the true cluster for gap #1 may be modestly larger
  than 287, not the full 934 the raw number implies.

## Part 2 — unsupervised clustering for candidates keyword matching never targeted

11 cluster(s) found that are large (>= 30 reviews), complaint-dominated (mean rating <= 2.5), and mostly NOT covered by any existing keyword filter (<= 35% overlap). Each is reported below with sample reviews for a human judgment call -- **none of these are added to gaps.json**; they have not been through roadmap cross-checking, confidence scoring, or falsification.

### Cluster 1 — 349 reviews, mean rating 2.1, 1% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00013` (rating=2): Not opening
- `review-play-00019` (rating=1): Not working
- `review-play-00038` (rating=1): It doesn't install.. Reads to 100% and just freezes tried it twice and all same
- `review-play-00049` (rating=1): The splash screen time takes too long to load and lags a lot .
- `review-play-00057` (rating=1): Poor connectivity

### Cluster 24 — 282 reviews, mean rating 1.5, 5% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00053` (rating=1): Have downloaded the app but I would have to uninstall it because when I tried to sign up an error occurs saying my email is invalid
- `review-play-00095` (rating=1): Is this app is only available for verified accounts ?
- `review-play-00106` (rating=1): I have downloaded the app but no access????
- `review-play-00132` (rating=1): App has crashed on my 3x just trying to create an account. Try again another day
- `review-play-00172` (rating=3): People! Go to the website (not through the app) and enter your email address. There must be a bug with going through the app...give the developers time...they h

### Cluster 5 — 268 reviews, mean rating 2.0, 8% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00007` (rating=1): Keeps crashing on launch on pixel 7
- `review-play-00100` (rating=1): This app can't even start in my phone, the devs working on it better fix it before it gains many users...
- `review-play-00104` (rating=1): It keeps crashing when ever i open the app.
- `review-play-00105` (rating=1): Have install the app twice still not working
- `review-play-00175` (rating=1): Plagued with technical issues. It was a total pain to try and sign up with email errors. Once I got in I repeatedly had trouble with the size of the text, the a

### Cluster 14 — 250 reviews, mean rating 1.4, 2% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00134` (rating=1): Can't sign in or register maybe later keep working
- `review-play-00147` (rating=1): I can't even sign up
- `review-play-00187` (rating=1): Can't login
- `review-play-00322` (rating=1): Not able to login and why are they giving hosting provider option?
- `review-play-00346` (rating=1): It sucks,too slow and it keeps loggin me out. Now i can't login with my original password.

### Cluster 22 — 217 reviews, mean rating 1.9, 0% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00002` (rating=3): Hi anyone has invite code?
- `review-play-00006` (rating=4): Someone please share me an invitation code. I am eagerly waiting to use and test the app
- `review-play-00010` (rating=5): Fantastic just like old twitter, got some invite codes I'll give to friends
- `review-play-00014` (rating=2): It requires Sign up code
- `review-play-00015` (rating=2): I don't have any experience. How exactly do we get the invitation code?

### Cluster 28 — 187 reviews, mean rating 1.4, 4% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00047` (rating=1): Why is the user name not working this not cool
- `review-play-00097` (rating=1): I can't create account. It is requesting invite code.
- `review-play-00123` (rating=2): Having difficulties creating the new account
- `review-play-00154` (rating=3): Couldn't enter my email either but if you scroll down to developer and hit website it will allow you to enter it. Hopefully this is the answer we need to musk's
- `review-play-00290` (rating=1): Can't create an account. I signed up on the waitlist last year and still haven't gotten an invite.

### Cluster 25 — 172 reviews, mean rating 1.6, 27% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00126` (rating=1): Second attempt of scam and same owner of jawaeye. Please don't waisted your time and money.
- `review-play-00173` (rating=5): It's great I'm zill yey app review and you better gimme some invites for this cuz what I'm gonna do is take those invites and make a hundred bot accounts to reb
- `review-play-00668` (rating=1): Since giving my email address to get a sign up code I've had nothing but spam in my email
- `review-play-00706` (rating=1): Seems fake. No way to make an account? I see a few people I follow elsewhere that post their Bluesky account, but you can't ever see it without an account? Yet 
- `review-play-00767` (rating=1): After more than eight months & scores of weighty updates, this fictional thing has delivered sweet nothing. Even its so-called "invitation" notices fail & there

### Cluster 12 — 166 reviews, mean rating 2.5, 1% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-01000` (rating=4): Can you please relocate the top button? It's a bit annoying in the way when scrolling with your left thumb.
- `review-play-01080` (rating=2): Huge problematic bug The text input does not refresh when I type, making it very difficult to write a post. If I open my app drawer it will refresh, but I shoul
- `review-play-01090` (rating=3): Update.. Please just put the timeline like twitter. The way the posts are loaded it's all over the place I want the latest post there and then scroll like I do 
- `review-play-01094` (rating=3): It's really annoying when you're trying to scroll up and down and it switches tabs side to side. It's far too sensitive. The app in general is a bit slow on And
- `review-play-01131` (rating=3): Generally works alright, but with the most recent update it refreshes itself and forces me back to the top of the timeline every once in awhile. Very annoying.

### Cluster 29 — 145 reviews, mean rating 1.6, 23% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00008` (rating=1): Not yet available, requires waitlist
- `review-play-00020` (rating=1): OK, it finally arrives on Android. So what? The "we'll be in touch shortly" message I got when I joined the waitlist in February didn't specify how they define 
- `review-play-00032` (rating=4): Not really felt the vibes of it. Currently on waitlist.
- `review-play-00046` (rating=2): Why release for all on Android if there js a waitlist. Just to occupy space on your phone. Or just to show more downloads?
- `review-play-00070` (rating=2): When I try to enter my email for the waiting list the keyboard keeps disappearing

### Cluster 7 — 94 reviews, mean rating 1.3, 0% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-01802` (rating=5): Speaking from a python dev and a cyber security expert I think the implementation of Captcha and some endpoints in this application was the best option ever as 
- `review-play-01872` (rating=1): ???? I can't even get pass the captcha phase. Bad gateway, upstream timeout, upstream failure. Guess I am a robot now?
- `review-play-01971` (rating=1): Verifying that not a robot is taken somuch time and not work.
- `review-play-02114` (rating=1): Could not get past captcha for an initial login/account setup. After at least 5 attempts. Edit: got a response that this is known problem. But it hasn't been fi
- `review-play-02473` (rating=1): Bet it's nice if you can get past the Captcha. Tried the app, tried the website, the Captcha comes up and says "complete the challenge" then shows a bunch of pi

### Cluster 20 — 46 reviews, mean rating 1.3, 0% already covered

*Flagged by semantic pass, not yet validated through the falsification pipeline -- your judgment call on whether this is a 4th gap candidate.*

- `review-play-00156` (rating=1): A liberal echo chamber
- `review-play-01518` (rating=2): Basically a left-wing echo chamber.
- `review-play-02548` (rating=1): Left wing echo chamber
- `review-play-02811` (rating=1): Really poor user experience. Just seems like a place to go for leftist propaganda, an intentional echo chamber.
- `review-play-02821` (rating=1): Awful echo chamber, too much censorship.

## Synthesis — reading the 11 flagged clusters (human judgment pass)

Automated flagging surfaces candidates; it doesn't validate them. Reading all 11
in full (not just the 5-sample excerpts above) and checking timestamps where it
mattered:

**Already considered in the original analysis, correctly excluded, not new (5 of 11):**
Clusters 22, 28, 29 (and most of 25) are all the same invite-code/waitlist theme
found and deliberately excluded during the original pass -- confirmed here by
timestamp (`review-play-00002`, `-00097`, `-00008` all land in April 2023, the
same historical window). Cluster 20 is the same partisan "echo chamber" language
excluded on SPEC.md §7 non-goal grounds. Both exclusions hold up under this
independent pass rather than being contradicted by it.

**Likely the same underlying failure mode, split by KMeans (4 of 11, not
independently novel but worth a look together):** Clusters 1, 5, 14, and 24 all
read as flavors of "the app fails before I can even use it" -- won't install,
freezes on splash screen, crashes on launch, sign-up throws an "invalid email"
error, crashes during account creation. These four clusters total roughly 1,150
reviews and overlap conceptually with the shipped login-keyboard gap (onboarding
is broken) without being the same specific symptom -- none of the samples
mention the keyboard flashing/closing. This reads like a broader "onboarding/
launch reliability" problem that the keyword-based gap #1 only captured one
slice of. Genuinely worth a follow-up pass (roadmap cross-check + falsification)
if a 4th gap slot is wanted, but it was not run here.

**Two genuinely new, coherent candidates, not previously considered at all:**

- **Cluster 7 (94 reviews, mean rating 1.3) — CAPTCHA blocks sign-up/login.**
  Distinct, specific, and recurring: "bad gateway, upstream timeout, upstream
  failure," "could not get past captcha for an initial login/account setup
  after at least 5 attempts... got a response that this is a known problem, but
  it hasn't been fixed." This is the strongest single new finding from this
  pass -- coherent, in the users' own words describes a concrete blocking bug,
  and one reviewer explicitly reports the team acknowledged it without fixing
  it. Not in `rejected_candidates.jsonl` and not covered by any shipped gap.
- **Cluster 12 (166 reviews, mean rating 2.5) — feed/scroll-position
  instability.** "Refreshes itself and forces me back to the top of the
  timeline," "scroll up and down and it switches tabs side to side, far too
  sensitive," "text input does not refresh when I type." A coherent UX
  complaint distinct from all three shipped gaps.

**Bottom line:** the semantic pass did its job -- it confirmed the two
already-excluded themes were correctly excluded, and it surfaced one strong
candidate (CAPTCHA) and one plausible one (feed/scroll instability) that
keyword search never targeted. Neither has been roadmap-cross-checked, scored,
or falsification-tested; per the brief, neither is added to `gaps.json`.
