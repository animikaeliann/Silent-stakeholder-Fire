# Semantic falsification report

Upgrades the falsification check from literal keyword search ("fixed," "resolved," "works now") to semantic similarity against 10 varied resolution-language exemplars, threshold 0.3 (calibrated below). Run against all 4 shipped gaps and all 3 rejected candidates.

## Threshold calibration

Known-positive regression check: PASSED. The two reviews already known (from the original keyword-based falsification) to report the video-crash bug fixed:
- `review-play-06529` (score 0.579): "Fixed the issue I had with videos crashing the app. Works great now!"
- `review-play-06841` (score 0.336): "Thank you for finally fixing the video crashing and removing AI bait posts from discover feed!"
Three unrelated control reviews (generic praise, an unrelated complaint, generic "works well" text) scored 0.216-0.285 in the calibration pass documented in this script's docstring -- 0.3 clears both known-positives with margin and stays above every control.

## Shipped: Users can't sign in or join the waitlist because the on-screen keyboard flashes …

Cluster size: 287. Flagged by raw semantic similarity (>= 0.3): 251 -- of which 89 carry an explicit negation cue ("still," "not fixed," "same issue," ...) and are almost certainly false positives from the embedding's known weakness on negation/polarity, leaving **162 worth an actual human read**.

Worth a human read (no negation cue detected):
- `review-play-06938` (score 0.496): Waiting for an update, so I can sign into the app. Keyboard only flashes on screen and does not allow me to sign in.
- `review-play-07212` (score 0.482): They fixed the bug where the keyboard disappears when I try to log in with my password, only for them to not fix it when I try to type in my confirmat
- `review-play-03466` (score 0.469): Same as some others, impossible to enter details on log in because keyboard pops up momentarily and then disappears. Needs sorting please.
- `review-play-00158` (score 0.464): Keyboard disappears every time I tap the text box to put my email on the wait list for the public beta
- `review-play-05692` (score 0.462): Can't sign in the keyboard flashes then closes before i can put my log in information in the website version works fine but as of right now i can't us
- `review-play-05755` (score 0.451): Every time when I try to login it always brings down my keyboard for some reason.. And when I get close to signing in it just says my login informatio
- `review-play-05514` (score 0.450): Keyboard closes immediately as soon as it opens. Unable to log into the app.
- `review-play-06731` (score 0.445): Can't even sign in. Keyboard disappears when I try.

Sample of the 89 likely false positive(s) (negation cue present):
- `review-play-00343` (score 0.518): The same waitlist keyboard problem as with many others. Apparently problem has persisted for weeks and nothing's done...
- `review-play-07093` (score 0.505): The login keyboard bug described by others is still present.
- `review-play-07979` (score 0.481): Originally posted on 01/24/2025. Almost 2 months later (03/20/2025): STILL CAN'T SIGN IN. SAME ISSUE STILL EXISTS. Can't sign in via the app because i

**No change, after a manual read.** Every one of the highest-scoring "worth review" reviews is still a complaint ("waiting for an update," "needs sorting please," "unable to log into the app") phrased without literally containing a negation cue from the blunt filter list above -- not a resolution claim. One genuine nuance: `review-play-07212` reports the password-field keyboard bug was fixed but the SAME bug persists on the confirmation-code field -- a real partial fix, not a full resolution of this gap's need (a reliably working login keyboard). Verdict unchanged: UNDER-PRIORITIZED, still open.

## Shipped: Users have no way to stop bot/spam accounts from following them: there is no pri…

Cluster size: 67. Flagged by raw semantic similarity (>= 0.3): 8 -- of which 1 carry an explicit negation cue ("still," "not fixed," "same issue," ...) and are almost certainly false positives from the embedding's known weakness on negation/polarity, leaving **7 worth an actual human read**.

Worth a human read (no negation cue detected):
- `review-play-01329` (score 0.366): Definitely missing some key features like being able to have a private account and two factor authentication. Hoping to see that in the future for the
- `review-play-02489` (score 0.345): While I love Bluesky for being twice as better than X (formerly Twitter), it does show it's flaws like your blocklist being public, remove follower fe
- `review-play-05441` (score 0.334): Loading app is slow. Sharing from the web doesn't register without being on the site prior to sharing. We need a remove followers option. Other than t
- `review-play-01613` (score 0.324): needs an option to make the account private!!
- `review-play-02107` (score 0.322): Add private account feature AND MY LIFE IS YOURSSSS 🙏 also currently very laggy please fix asap I can barely scroll and like
- `review-play-05013` (score 0.322): Can't sent pics over DM, no private accounts, no translation of posts, can't bookmark posts, weird algorithm pushing junk posts and proliferation of b
- `review-play-01347` (score 0.309): Two things prevent me from giving 5☆. You have to follow loads to see all the feeds & you can't remove a follower you can only mute or block.

Sample of the 1 likely false positive(s) (negation cue present):
- `review-play-04671` (score 0.304): Still needs a few more features like remove follower and drafts but other wise great app

**No change, after a manual read.** All 7 "worth review" reviews are feature requests ("needs an option to make the account private!!", "we need a remove followers option") -- asking for the feature, not reporting it exists. Zero resolution signals. Verdict unchanged: UNDER-PRIORITIZED, still open.

## Shipped: Follower counts and follower lists don't reflect reality: blocked accounts still…

Cluster size: 15. Flagged by raw semantic similarity (>= 0.3): 2 -- of which 1 carry an explicit negation cue ("still," "not fixed," "same issue," ...) and are almost certainly false positives from the embedding's known weakness on negation/polarity, leaving **1 worth an actual human read**.

Worth a human read (no negation cue detected):
- `review-play-05668` (score 0.321): Nice app. Notifications don't work on my new Galaxy s24 Ultra. Nothing. Update: fixed it by deleting app data and logging in again 🤷. Keep improving t

Sample of the 1 likely false positive(s) (negation cue present):
- `review-play-06263` (score 0.374): The follwer count is acting up. My profile says I have 17 when I can only see 7? I tried refreshing and logging out, nothing changed.

**No change, after a manual read.** The 1 "worth review" result (`review-play-05668`) is about a *different* bug (notifications not working on a specific device) fixed via a user-side workaround (deleting app data) -- not the shipped gap's follower-count/blocked-user issue, and not an official fix even for the bug it does describe. Verdict unchanged: UNDER-PRIORITIZED, still open.

## Shipped: A broken CAPTCHA/verification step blocks account creation and login for a signi…

Cluster size: 87. Flagged by raw semantic similarity (>= 0.3): 35 -- of which 10 carry an explicit negation cue ("still," "not fixed," "same issue," ...) and are almost certainly false positives from the embedding's known weakness on negation/polarity, leaving **25 worth an actual human read**.

Worth a human read (no negation cue detected):
- `review-play-06435` (score 0.438): terrible set up. try many times to prove I'm not a robot. then when I finally did that. couldn't get the app to allow to up load profile imagine. trie
- `review-play-02743` (score 0.415): Got frustrated at the final stage of the sign up, due to their annoying CAPTCHA process. Had to abandon it entirely
- `review-play-04499` (score 0.415): Captcha took ages, then app repeatedly crashed on start up, then update app, then repeatedly crashed...but then worked
- `review-play-03245` (score 0.367): Complete nonsense with the hcaptcha, i keep verifying with images inside the box correctly and they keep telling me to "please try again" fix it or ju
- `review-play-03028` (score 0.356): For some reason I can't seem to pass the captcha page. Can someone from the technical department fix this 🤦🏽♂️
- `review-play-05227` (score 0.355): I was having trouble opening account for days because of the captcha. I got a tip on Reddit to use a VPN to create the account which worked perfectly.
- `review-play-02631` (score 0.351): Unable to get past the am I a robot section as the pics you needed to match were never in the suggestions. Tried support and got no response. Uninstal
- `review-play-02749` (score 0.349): Signing up is frustrating. Your captchas don't work and keeps telling me to try again. Rectify please.

Sample of the 10 likely false positive(s) (negation cue present):
- `review-play-03253` (score 0.406): I can't even sign in the hCaptcha is a mess I've contacted support an nothing was really fixed I reported it on hCaptcha as a bug still nothing and it
- `review-play-04763` (score 0.388): I haven't been able to sign up because the captcha is not working.
- `review-play-08095` (score 0.383): can't even log in the captcha isn't working

**No change, after a manual read.** All 25 "worth review" reviews are either unresolved complaints/requests-to-fix, or describe USER-SIDE WORKAROUNDS (e.g. `review-play-05227`: "got a tip on Reddit to use a VPN... which worked perfectly") rather than an official fix -- if anything, a workaround being necessary is corroborating evidence the underlying bug is real and unaddressed, not evidence against it. One ambiguous case (`review-play-04499`: "...repeatedly crashed...but then worked") reads as eventually getting through after retrying, not a confirmed fix. Verdict unchanged: UNDER-PRIORITIZED, still open.

## Rejected: App crashes every time a user tries to open/play a video (full-screen or inline)…

Cluster size: 32. Flagged by raw semantic similarity (>= 0.3): 26 -- of which 3 carry an explicit negation cue ("still," "not fixed," "same issue," ...) and are almost certainly false positives from the embedding's known weakness on negation/polarity, leaving **23 worth an actual human read**.

Worth a human read (no negation cue detected):
- `review-play-06529` (score 0.579): Fixed the issue I had with videos crashing the app. Works great now!
- `review-play-05831` (score 0.468): ever since the December 20 update, the app crashes whenever I click on a video. Latest: after the December 31st update, all is well again :)
- `review-play-06540` (score 0.462): Newest update crashed the app. Video feeds wasn't added and it doesn't scroll anymore. If this doesn't get fixed, it's a hard uninstall
- `review-play-04128` (score 0.388): I've been running into a lot of bugs, random crashes and things like my profile info not saving. I've been getting errors when I try to post pictures 
- `review-play-06108` (score 0.383): the app crashes for mobile as you click on posts that have video.
- `review-play-05921` (score 0.377): I go to play a video and it crashes app, updates at all?
- `review-play-05789` (score 0.372): Every time I click on a video the app crashes.
- `review-play-05886` (score 0.367): the app and structure are great, i love it, i just wish it worked. the app crashes outright whenever i try to upload a photo or video, and also whenev

Sample of the 3 likely false positive(s) (negation cue present):
- `review-play-05965` (score 0.467): Pretty good, but the full screen video crashes are not fixed even if the latest update says they are.
- `review-play-05839` (score 0.336): Crashes every time I try to open a video - this bug has persisted for over a week now. I'm on the latest version of Android 9, using a Samsung Galaxy 
- `review-play-05856` (score 0.324): App crashes everytime I click on a video. It didn't do that before. Android user here. I just uninstalled and installed the app again because I heard 

Confirms the original falsification reasoning for this rejected candidate.

## Rejected: Users want the ability to turn on notifications for individual accounts' new pos…

Cluster size: 21. Flagged by raw semantic similarity (>= 0.3): 4 -- of which 1 carry an explicit negation cue ("still," "not fixed," "same issue," ...) and are almost certainly false positives from the embedding's known weakness on negation/polarity, leaving **3 worth an actual human read**.

Worth a human read (no negation cue detected):
- `review-play-02488` (score 0.325): I would dearly like to see post notifications from those I wish to get notified from. Right now I think it's the most glaring omission. Please conside
- `review-play-04701` (score 0.321): 2 things bug me about this app... 1) The splash screen every single time I open the app. At least give an option in the settings to turn that off. So 
- `review-play-06798` (score 0.303): Needs post notifications, badly

Sample of the 1 likely false positive(s) (negation cue present):
- `review-play-04577` (score 0.306): I can't get post notifications, I get no options to do so. If this app works fine for Apple but doesn't work properly for Android, then Bluesky is wor

**Out of scope for this check, not a failure of it:** this candidate's original falsification evidence was a *different GitHub issue* proving the feature already shipped, not review text describing a fix -- there is no review in this corpus that could semantically resemble 'this got fixed' for a feature the reviewers themselves were still requesting. The rejection stands on its original (non-review) evidence regardless of what this review-text-only method finds.

## Rejected: Accounts get suspended/labeled with no explanation or a slow/absent appeal proce…

Cluster size: 78. Flagged by raw semantic similarity (>= 0.3): 17 -- of which 0 carry an explicit negation cue ("still," "not fixed," "same issue," ...) and are almost certainly false positives from the embedding's known weakness on negation/polarity, leaving **17 worth an actual human read**.

Worth a human read (no negation cue detected):
- `review-play-07368` (score 0.395): The app sucks it keeps suspending accounts for no reason, it's wrong
- `review-play-07315` (score 0.360): Have had a wonderful experience until my account was suspended early this morning. I did nothing wrong and used the app as intended. Was recently adde
- `review-play-08290` (score 0.358): I signed up and had barely scrolled through my feed only to find that my account has been suspended? just like that? like seconds after I sign up? I d
- `review-play-07698` (score 0.354): Don't even bother to download the app,i just opened an account and it's been suspended don't waste your time trying to download the app
- `review-play-07797` (score 0.349): Update: my account got suspended because I followed too many people lol. This is ridiculous! ------ I got an 'inpersonation label' just because my nam
- `review-play-07769` (score 0.344): I love the app. But they have suspended my account.
- `review-play-08068` (score 0.342): As if it isn't buggy enough, they suspend accounts for literally no reason and never respond when you email to get them to review. Don't waste your ti
- `review-play-08019` (score 0.333): Useless app suspending me without clear explanation of my exact issue.

**Not a falsification-based rejection, so this check doesn't apply to why it was excluded.** This candidate was rejected on SPEC.md §7 scope grounds (confounded with partisan sentiment), not because it was found already resolved -- resolution-language similarity is simply the wrong lens here. The flagged reviews above are just complaints about the underlying moderation experience, not evidence for or against the original scope-exclusion reasoning, which stands unchanged.

## Overall

**No change in any conclusion, after manually reading every negation-filtered "worth review" result.** All 4 shipped gaps: no genuine resolution signal, only complaints and user-side workarounds phrased with resolution-adjacent vocabulary (see each section above for specifics). All 3 rejected candidates check out on their own terms: video-crash's review-text-based falsification is correctly reproduced; the notification-feature rejection's real evidence (a GitHub issue, not review text) is correctly out of scope for this method; the moderation-appeal rejection was never resolution-based to begin with (a SPEC.md §7 scope exclusion), so this check doesn't speak to it either way. "No change, confirms robustness" is the finding here, not an absence of one -- and getting there required manually reading the flagged output, since the raw automated counts (up to 251/287 for one gap) were dominated by a real, demonstrated negation-blindness problem in the embedding similarity approach, not genuine signal.
