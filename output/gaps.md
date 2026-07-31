# The Silent Stakeholder — Gap Analysis: Bluesky

**4 gaps shipped**, ranked strongest evidence first. **3 candidates investigated and rejected** via falsification (see log below) rather than silently dropped.

Source: 8,359 Google Play reviews for Bluesky (2023-04-19 to 2025-04-20) cross-checked against the live `bluesky-social/social-app` GitHub issue tracker.

**Scope note:** the roadmap side of this analysis is unauthenticated-GitHub-API scope: all currently open issues + all milestones, but **no closed-issue history** (see Limitations at the bottom). A gap that looks IGNORED or UNDER-PRIORITIZED here could in principle have a closed, already-merged fix we can't see — each gap's falsification check is the safeguard against that, not the roadmap scope alone.

---

## #1 — Users can't sign in or join the waitlist because the on-screen keyboard flashes open and immediately closes on the username/password/email field, blocking account access entirely on some Android devices.

**Verdict:** `UNDER-PRIORITIZED`  |  **Confidence:** `0.95`

> 287 independent reviews (2023-04-24 to 2025-04-19) describe this need. #6264: no milestone AND stale (620d since last update, threshold 180d); #2371: no milestone AND stale (944d since last update, threshold 180d)

**Confidence math:**

```
corroboration=1.0 (n=287 distinct reviews / 15 cap) * 0.35 = 0.35; signal_count=1.0 (n=287 / 100 cap) * 0.25 = 0.25; latency=1.0 (span=726d / 365 cap) * 0.20 = 0.2; roadmap_disconfirmation=0.8 * 0.20 = 0.16. Sum=0.96 -> rounded to nearest 0.05 = 0.95. Disconfirmation basis: #6264: no milestone AND stale (620d since last update, threshold 180d); #2371: no milestone AND stale (944d since last update, threshold 180d).
```

**Evidence:**

- *[primary]* (`review-play-04353`): I can't even log in on the app, I can use the app on my Apple device but not here. Seems like a lot of the problems have to do with Samsung devices on the Google Play Store. Every time I click to enter my email or any information it shuts down right away. ***UPDATE*** It's a keyb
- *[corroborating]* (`review-play-04921`): It would be nice if it was possible to actually sign into the app on my phone. When trying to do so, the keyboard flashes and immediately disappears. This has been ongoing now for a month. I was signed out and have never been able to get back in. It's a useless app until then, wh
- *[corroborating]* ([github-issue-6264](https://github.com/bluesky-social/social-app/issues/6264)): Unable to login on Android; Samsung S22.  ### Steps to Reproduce  1. Go to login screen. 2. Select login field. 3. The screen jumps as keyboard pulls up. 4. The login field is deselected. 5. Password field jumps the same way.  ### Attachments  _No response_  ### What platform
- *[corroborating]* ([github-issue-2371](https://github.com/bluesky-social/social-app/issues/2371)): User handle input broken with some Android keyboards  This is not new, but we've managed to improve support for various keyboards in the composer, and we should return to this to see what we can do here.  https://github.com/bluesky-social/social-app/assets/4732330/f1ec0c2c-5e27-4

**Roadmap cross-references:**

- [github-issue-6264](https://github.com/bluesky-social/social-app/issues/6264) — exact match: same symptom (login field keyboard opens then closes/deselects on Android), same repro steps
- [github-issue-2371](https://github.com/bluesky-social/social-app/issues/2371) — adjacent-narrower: same class of Android keyboard/input bug, but scoped to composer handle-input, not the login screen

**Alternative explanations considered and rejected:** Could this be device fragmentation noise (one bad OEM keyboard) rather than a real product gap? Ruled out: reports name Samsung Galaxy S8/S20/S22/S24 and Pixel 6a across Android 9 through 14, spanning 6 dot releases of the app over two years -- a single-device explanation does not fit a defect this wide or this durable.

---

## #2 — A broken CAPTCHA/verification step blocks account creation and login for a significant share of users: it fails to render, times out with a gateway error, or rejects a correctly-completed challenge with an 'invalid verification code' error.

**Verdict:** `UNDER-PRIORITIZED`  |  **Confidence:** `0.95`

> 87 independent reviews (2023-12-24 to 2025-04-04) describe this need. #6704: no milestone AND stale (611d since last update, threshold 180d); #6936: no milestone AND stale (603d since last update, threshold 180d)

**Confidence math:**

```
corroboration=1.0 (n=87 distinct reviews / 15 cap) * 0.35 = 0.35; signal_count=0.87 (n=87 / 100 cap) * 0.25 = 0.2175; latency=1.0 (span=467d / 365 cap) * 0.20 = 0.2; roadmap_disconfirmation=0.8 * 0.20 = 0.16. Sum=0.9275 -> rounded to nearest 0.05 = 0.95. Disconfirmation basis: #6704: no milestone AND stale (611d since last update, threshold 180d); #6936: no milestone AND stale (603d since last update, threshold 180d).
```

**Evidence:**

- *[primary]* (`review-play-04131`): Why did I give this app one star is because I did not even log into the app and see the feature of the cause of CAPTCHA verification even if you are woman that thing is not verifying you that is it and that is the truth you people have to remove that thing totally from your app t
- *[corroborating]* (`review-play-04148`): Really!!! Replace X? This app is a complete joke. Meanwhile I had fun playing with the Captcha, with the endless circle of retries with different Captchas, I guess you guys got that right. Do your self one favour, change your org to a captcha game company, it will do the public s
- *[corroborating]* ([github-issue-6704](https://github.com/bluesky-social/social-app/issues/6704)): Sign-Up Captcha does not display correctly on some displays in a way that prevents use [Android]  ### Steps to Reproduce  1. Open bluesky app on the internal screen of Galaxy Fold 4 (potentially other foldables and tablets too, but I don't have any to test) 2. Attempt to create
- *[corroborating]* ([github-issue-6936](https://github.com/bluesky-social/social-app/issues/6936)): can't create a new account - captcha fails to render  ### Steps to Reproduce  1. visit https://bsky.app in empty browser (Safari, Chrome incognito) 2. choose new account, fill in email etc. 3. choose a new handle, click next   <img width="720" alt="image" src="https://github

**Roadmap cross-references:**

- [github-issue-6704](https://github.com/bluesky-social/social-app/issues/6704) — exact match: sign-up captcha fails to display correctly on some Android devices (foldables/tablets), preventing completion
- [github-issue-6936](https://github.com/bluesky-social/social-app/issues/6936) — exact match: captcha fails to render during account creation on web

**Alternative explanations considered and rejected:** Could this just be users failing the challenge (user error) rather than a real bug? Ruled out: reports describe specific technical failure modes -- 'bad gateway, upstream timeout, upstream failure', the prompt rendering cut off on foldable/tablet displays, and 'invalid verification code' errors appearing immediately after a challenge is correctly completed, not after a wrong answer; one reviewer reports the team acknowledged this as 'a known problem' that 'hasn't been fixed'. Could this double-count the shipped login-keyboard-dismissal gap? Ruled out by checking directly: zero review-id overlap between the two keyword clusters, and the failure modes are unrelated (keyboard focus vs. captcha rendering/validation). Device/platform diversity across the cluster (Android app, Chrome/Safari incognito web, Samsung Galaxy Fold, tablets) rules out single-device fragmentation as the explanation.

---

## #3 — Users have no way to stop bot/spam accounts from following them: there is no private/locked account option, and no way to remove an unwanted follower without blocking them.

**Verdict:** `UNDER-PRIORITIZED`  |  **Confidence:** `0.85`

> 67 independent reviews (2024-03-07 to 2025-04-07) describe this need. #1155: open 1082d (2y+) and never scheduled to a milestone, despite recent comment activity; #1160: open 1081d (2y+) and never scheduled to a milestone, despite recent comment activity

**Confidence math:**

```
corroboration=1.0 (n=67 distinct reviews / 15 cap) * 0.35 = 0.35; signal_count=0.67 (n=67 / 100 cap) * 0.25 = 0.1675; latency=1.0 (span=396d / 365 cap) * 0.20 = 0.2; roadmap_disconfirmation=0.65 * 0.20 = 0.13. Sum=0.8475 -> rounded to nearest 0.05 = 0.85. Disconfirmation basis: #1155: open 1082d (2y+) and never scheduled to a milestone, despite recent comment activity; #1160: open 1081d (2y+) and never scheduled to a milestone, despite recent comment activity.
```

**Evidence:**

- *[primary]* (`review-play-02336`): Has room for improvement. For example: needs ability to make locked/private accounts. Needs a bookmark feature. Maybe the ability to show/hide our likes tab on our profile. Sometimes I like to share art I've found with friends this way. Moderation could do with some tweaking as I
- *[corroborating]* (`review-play-04510`): Needs a way to remove individual unwanted followers. There are enough users that I'm now starting to get fake account follows and I want to remove them.
- *[corroborating]* ([github-issue-1155](https://github.com/bluesky-social/social-app/issues/1155)): Private/Locked accounts  The option to make your account "private" as in only your followers can see your posts.
- *[corroborating]* ([github-issue-1160](https://github.com/bluesky-social/social-app/issues/1160)): Ability to remove a follower  Feature request: Ability to remove a follower from your followers, either via soft block (block and unblock) or via a simple remove process.  At present if you block someone, and then unblock them later they are still following you .. this can be u

**Roadmap cross-references:**

- [github-issue-1155](https://github.com/bluesky-social/social-app/issues/1155) — exact match: request for private/locked accounts
- [github-issue-1160](https://github.com/bluesky-social/social-app/issues/1160) — exact match: request for ability to remove a follower without blocking

**Alternative explanations considered and rejected:** Could this just be generic anti-spam sentiment rather than a specific, buildable feature ask? Ruled out: the review text converges on two concrete, named feature requests (account privacy toggle, follower removal) that already match filed, multi-hundred-comment GitHub issues -- this is not vague dissatisfaction, it is a request the team has already scoped.

---

## #4 — Follower counts and follower lists don't reflect reality: blocked accounts still count as followers and still appear in follower lists, and displayed follower counts are simply inconsistent/wrong on refresh.

**Verdict:** `UNDER-PRIORITIZED`  |  **Confidence:** `0.65`

> 15 independent reviews (2024-09-03 to 2025-04-18) describe this need. #853: no milestone AND stale (604d since last update, threshold 180d); #7370: no milestone AND stale (187d since last update, threshold 180d)

**Confidence math:**

```
corroboration=1.0 (n=15 distinct reviews / 15 cap) * 0.35 = 0.35; signal_count=0.15 (n=15 / 100 cap) * 0.25 = 0.0375; latency=0.6219 (span=227d / 365 cap) * 0.20 = 0.1244; roadmap_disconfirmation=0.8 * 0.20 = 0.16. Sum=0.6719 -> rounded to nearest 0.05 = 0.65. Disconfirmation basis: #853: no milestone AND stale (604d since last update, threshold 180d); #7370: no milestone AND stale (187d since last update, threshold 180d).
```

**Evidence:**

- *[primary]* (`review-play-07735`): It's ok if u want smthg better than toxic X..downsides to this app are: u can't set profile private, blocks are public (meaning they're still part of follower count)..but can't interact. Needs edit button..or you will have to delete & redo post, which is very annoying. Needs an a
- *[corroborating]* (`review-play-05862`): Need to have the ability to make accounts private, remove blocked followers and there are too many spam accounts wanting to follow.
- *[corroborating]* ([github-issue-853](https://github.com/bluesky-social/social-app/issues/853)): Blocked people are still able to follow and show up in the followers also follower count  I tried to fix it:  _appendAll(res: GetFollowers.Response) {   this.loadMoreCursor = res.data.cursor;   this.hasMore = !!this.loadMoreCursor;   const filteredFollowers = res.data.follow
- *[corroborating]* ([github-issue-7370](https://github.com/bluesky-social/social-app/issues/7370)): Follower count is incorrect  ### Steps to Reproduce  1. Go to profile page (my page is @stonemilled.bsky.socal) 2. Click 12 followers 3. Note that there are not 12 followers. This weirdly varies how many it shows (on some renders it shows spam bots, on others it doesn't)  ### A

**Roadmap cross-references:**

- [github-issue-853](https://github.com/bluesky-social/social-app/issues/853) — exact match: blocked accounts still counted/shown as followers
- [github-issue-7370](https://github.com/bluesky-social/social-app/issues/7370) — exact match: follower count displays incorrect/inconsistent number

**Alternative explanations considered and rejected:** Could this be the same underlying need as the private-account gap above, just double-counted? Ruled out: this cluster reports a data-integrity bug (the number/list is factually wrong) rather than a missing privacy control (no way to prevent following in the first place) -- different roadmap issues, different fixes, kept as a separate gap. Only 1 review overlaps between the two evidence sets.

---

## Rejected candidates (falsification log)

Candidates that were investigated and did *not* ship, with the specific disconfirming evidence — included so the room can see what was ruled out, and why, not just what made the cut.

### 1. App crashes every time a user tries to open/play a video (full-screen or inline).

**Reason:** falsified: resolved during the data window. 30 independent complaints cluster tightly between 2024-12-23 and 2025-01-21 (traceable to a 'December 20 update' named in-review), then reviews from 2025-01-21 onward explicitly say the crash is fixed ('Fixed the issue I had with videos crashing the app', 'Thank you for finally fixing the video crashing') and complaint volume drops to ~0/month afterward. Shipping this as a live gap would mislead the room into re-litigating an already-fixed bug.

**Supporting evidence ids:** review-play-05618, review-play-06529, review-play-06841

### 2. Users want the ability to turn on notifications for individual accounts' new posts.

**Reason:** falsified: feature appears to already exist. The ask (review-play-06244, review-play-06302, both 2025-01) matches a per-account 'post notifications' feature that a much later open bug, github-issue-10662 ('Post notifications override notifications for replies/quotes', updated 2026-05-30), describes as already live and malfunctioning -- i.e. the feature request was fulfilled; what remains is a narrower bug, not this gap.

**Supporting evidence ids:** review-play-06244, review-play-06302, github-issue-10662

### 3. Accounts get suspended/labeled with no explanation or a slow/absent appeal process.

**Reason:** rejected: signal is confounded with partisan sentiment about moderation policy ('anti free speech', 'liberal wet dream', 'gas chamber for Republicans'). SPEC.md §7 rules this project out as a sentiment dashboard and requires seeing 'both sides' -- the narrower, legitimately actionable complaint (opaque/slow appeals) cannot be cleanly separated from the political framing in this corpus without editorializing about which moderation decisions were correct, so it is left out rather than shipped on a shaky corroboration count.

**Supporting evidence ids:** review-play-04433, review-play-04966, review-play-05830


---

## Limitations for the live defense

- **GitHub roadmap fetched unauthenticated** (no `GITHUB_TOKEN` / `gh auth` available in this environment): open issues + all milestones only, closed-issue history out of scope. Logged as a reasoned decision in `logs/filtered.jsonl`, not a silent drop. This means IGNORED/UNDER-PRIORITIZED verdicts can't distinguish 'nobody filed this' from 'somebody filed and fixed this, then the issue was closed' — mitigated per-gap by checking whether review complaint volume itself drops off (a proxy for a real-world fix shipping).
- **Review corpus ends 2025-04-20**; the GitHub roadmap reflects live state as of the run date. There's a ~15-month blind window where user sentiment could have shifted on any of these three gaps without it showing up here.
- **Clustering is deterministic keyword matching**, not an ML/embedding-based semantic clustering — candidate needs and their roadmap cross-references were identified by manual reading of the corpus (documented in the pipeline script), which is reproducible and auditable but will miss paraphrased complaints that don't share the matched keywords.
- **One legitimate-looking candidate was excluded outright**, not scored down: a moderation-appeals complaint that the corpus expresses almost entirely through partisan language, which SPEC.md §7 rules out of scope for this exercise.
