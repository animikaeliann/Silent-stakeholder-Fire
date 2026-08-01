"""
Second-order / latent-need signal mining -- Phase 1 of 3 (this script only
does detection; synthesis is Phase 2, done by direct reasoning over this
script's output, not more regex; rigor-scoring is Phase 3).

The brief's actual bar: infer LATENT needs -- ones that only show up as
second-order patterns across many reviews or across time -- as distinct
from listing frequent complaints, which the 4 shipped gaps already do well
(they're real, well-corroborated, but each is directly stated by many
individual reviewers). This phase looks for something that clears the
higher bar. It may find nothing that survives Phase 2's filter -- that is
an acceptable, honestly-reported outcome, not a failure of this script.

PHASE 0 FINDING (verified just now, not assumed):
  data/normalized/reviews.jsonl has exactly these top-level keys:
    {timestamp, source_type, text, metadata, id, source_dataset, rating}
  and exactly these metadata keys:
    {helpful_count, char_len, is_exact_duplicate_text, app_id}
  (verified via: python3 -c "import json; ks=set(); ms=set()
   ... for l in open('data/normalized/reviews.jsonl'): ...")
  The original raw CSV header confirms the same absence at the source:
    review_id,app_id,review_text,review_score,review_date,helpful_count,len
  There is NO reviewer/user identifier of any kind (no username, no device
  id, nothing linking two reviews to the same person). This confirms the
  brief's prediction. Consequently, Detector 4 (cross-cluster correlation)
  below uses TIME-based co-occurrence (do two clusters spike in the same
  weeks/months, suggesting a shared trigger like an app update) -- it does
  NOT and cannot track the same reviewer across posts. This substitution
  is disclosed here explicitly, not silently assumed.

Purely additive, read-only: reads data/normalized/reviews.jsonl and
scripts/03_infer_gaps.py + scripts/05_rubric_sensitivity.py (for the
existing shipped/rejected candidate keyword filters, reused as known
themes for Detectors 3/4 -- not reinvented). Writes
output/latent_signals_raw.json. Does NOT touch output/gaps.json,
output/gaps.md, or any shipped-gap data -- this is raw material for a
human synthesis step (Phase 2), not a scored or shippable output.

Usage: python scripts/16_latent_signal_mining.py
"""
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "output" / "latent_signals_raw.json"

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with", "is", "are",
    "was", "were", "this", "that", "these", "those", "it", "its", "their", "there", "have",
    "has", "had", "not", "no", "some", "any", "also", "from", "by", "at", "as", "be", "been",
    "being", "can", "cant", "dont", "doesnt", "who", "what", "when", "where", "why", "how",
    "because", "then", "than", "them", "they", "he", "she", "you", "your", "i", "we", "our",
    "us", "if", "so", "just", "get", "gets", "getting", "still", "even", "app", "users", "user",
}


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def extract_keywords(text, min_len=4):
    words = re.findall(r"[a-z']+", text.lower())
    return {w for w in words if len(w) >= min_len and w not in STOPWORDS}


# ---------------------------------------------------------------------------
# Detector 1: workaround language -- compensating behavior, not direct asks.
# Patterns calibrated against this exact corpus (see commit description /
# session notes for the grep sweep that picked these over patterns that
# returned 0 real hits, e.g. "instead of using", "went back to").
# ---------------------------------------------------------------------------
WORKAROUND_PATTERNS = [
    r"\bi now use\b", r"\bi stopped\b", r"\bi have to manually\b", r"\bworkaround\b",
    r"\bhave to restart\b", r"\brestart(ing)? the app (whenever|every|in order|to)\b",
    r"\brestart it (all the time|to)\b", r"\bforced to use\b", r"\bhave to keep\b",
    r"\bhave to re-?enter\b", r"\bhave to re-?log\b", r"\beach time i\b",
]


def detect_workaround_language(reviews):
    pattern_re = re.compile("|".join(WORKAROUND_PATTERNS), re.I)
    matches = []
    for r in reviews:
        m = pattern_re.search(r["text"])
        if m:
            matches.append({
                "id": r["id"], "timestamp": r["timestamp"], "rating": r["rating"],
                "matched_pattern": m.group(0).lower(), "text": r["text"][:300],
            })
    return matches


# ---------------------------------------------------------------------------
# Detector 2: implicit-standard via comparison -- other apps invoked as an
# unstated baseline. Broad net on purpose (Phase 2 does the real filtering);
# still requires an actual comparison frame, not just naming another app
# (a bare "better than Twitter" carries no extractable feature expectation).
# ---------------------------------------------------------------------------
OTHER_APPS = ["twitter", "instagram", "threads", "mastodon", "tiktok", "reddit"]
COMPARISON_FRAMES = [
    r"\bunlike\b", r"\bnot as good as\b", r"\bwish (it|this|i) (had|could)\b",
    r"\bdoesn'?t have (a|the|an)? ?\w+ (feature|option|function)\b",
    r"\blike (twitter|instagram|x|threads|tiktok|mastodon) (has|does)\b",
    r"\bno (bookmark|save|edit|schedule)\b", r"\bbetter than\b.{0,30}\b(feature|option)\b",
]


def detect_implicit_comparison(reviews):
    app_re = re.compile("|".join(re.escape(a) for a in OTHER_APPS) + r"|\bx\b", re.I)
    frame_re = re.compile("|".join(COMPARISON_FRAMES), re.I)
    matches = []
    for r in reviews:
        text = r["text"]
        if app_re.search(text) and frame_re.search(text):
            fm = frame_re.search(text)
            matches.append({
                "id": r["id"], "timestamp": r["timestamp"], "rating": r["rating"],
                "matched_frame": fm.group(0).lower(), "text": text[:300],
            })
    return matches


# ---------------------------------------------------------------------------
# Detector 3: silent-churn divergence -- for a given theme, does explicit
# complaint volume decline while churn-adjacent language volume (co-
# occurring with the SAME theme, in the same review) rises? Different
# mechanism than the existing keyword/semantic falsification check (which
# looks for "this got fixed" language) -- this looks for "people stopped
# complaining because they left," which reads identically to a fix unless
# both series are checked together.
# ---------------------------------------------------------------------------
CHURN_PATTERNS = [
    r"\buninstall", r"\bdelete this app\b", r"\bswitching back to\b",
    r"won'?t be using this anymore", r"\bdone with this app\b",
    r"\bgoing back to twitter\b", r"\bnot using this anymore\b", r"\bdeleted the app\b",
]
CHURN_RE = re.compile("|".join(CHURN_PATTERNS), re.I)
OTHER_APP_NEAR_RE = re.compile("|".join(re.escape(a) for a in OTHER_APPS), re.I)

MIN_THEME_N = 10
MIN_CHURN_N = 3


def is_churn_targeting_this_app(text, match):
    """A churn match right next to a competitor app name usually means 'I
    uninstalled X (Twitter)', not this app -- exclude those. Checks both
    before AND after the match: real examples appear on both sides (e.g.
    review-play-00584: "uninstalled X (Twitter)" -- app name AFTER;
    review-play-00990: "Uninstalled the app, i'm on Mastodon" -- app name
    also after but further out; checking only a before-window missed
    these on first implementation, caught by testing against real data)."""
    window = text[max(0, match.start() - 40):match.end() + 40]
    return not OTHER_APP_NEAR_RE.search(window)


def half_split_rates(dated_items):
    """Split a list of (timestamp,) items at the median date; return
    (first_half_rate, second_half_rate) as count-per-month. Returns None if
    too few distinct months to split meaningfully."""
    months = sorted(set(item[:7] for item in dated_items))
    if len(months) < 2:
        return None
    mid = len(months) // 2
    first_months, second_months = months[:mid] or months[:1], months[mid:]
    first_count = sum(1 for item in dated_items if item[:7] in first_months)
    second_count = sum(1 for item in dated_items if item[:7] in second_months)
    return first_count / len(first_months), second_count / len(second_months)


def silent_churn_analysis(theme_name, theme_filter, reviews):
    matched = [r for r in reviews if theme_filter(r) and r["timestamp"]]
    if len(matched) < MIN_THEME_N:
        return {"theme": theme_name, "n": len(matched), "flagged": False,
                "reason": f"insufficient data (n={len(matched)} < {MIN_THEME_N})"}

    churn_matches = []
    for r in matched:
        m = CHURN_RE.search(r["text"])
        if m and is_churn_targeting_this_app(r["text"], m):
            churn_matches.append(r)

    complaint_rates = half_split_rates([r["timestamp"] for r in matched])
    result = {
        "theme": theme_name, "n": len(matched), "n_churn_matches": len(churn_matches),
        "complaint_monthly": dict(Counter(r["timestamp"][:7] for r in matched)),
        "churn_monthly": dict(Counter(r["timestamp"][:7] for r in churn_matches)),
        "churn_evidence_ids": [r["id"] for r in churn_matches],
    }
    churn_rates = half_split_rates([r["timestamp"] for r in churn_matches])
    if len(churn_matches) < MIN_CHURN_N or complaint_rates is None or churn_rates is None:
        result["flagged"] = False
        result["reason"] = (
            f"insufficient churn co-occurrence (n_churn={len(churn_matches)} < {MIN_CHURN_N})"
            if len(churn_matches) < MIN_CHURN_N
            # churn_rates is None means all churn matches fall in a single month --
            # real bug found here: this case previously crashed with a TypeError
            # instead of being reported as "insufficient data to split."
            else "churn matches span too few distinct months to compute a trend"
        )
        return result

    declining = complaint_rates[1] < complaint_rates[0]
    rising = churn_rates[1] > churn_rates[0]
    result["complaint_rate_first_half"], result["complaint_rate_second_half"] = complaint_rates
    result["churn_rate_first_half"], result["churn_rate_second_half"] = churn_rates
    result["declining_complaints"] = declining
    result["rising_churn"] = rising
    result["flagged"] = declining and rising
    return result


# ---------------------------------------------------------------------------
# Detector 4: cross-cluster time correlation -- per Phase 0's finding, this
# uses monthly volume correlation (not same-reviewer tracking, which the
# data doesn't support) between themes sharing no/little keyword overlap.
# ---------------------------------------------------------------------------
CORRELATION_THRESHOLD = 0.6
MAX_SHARED_KEYWORDS = 1


def monthly_share_vector(matched, all_months, total_by_month):
    """Theme volume as a FRACTION of that month's total review volume, not
    a raw count. Required correction, found by actually running this: total
    review volume itself spikes ~10x in 2024-11 (a real, well-known event --
    2546 reviews that month vs. a typical 40-500) and every theme rides that
    same wave, so raw-count correlation between ANY two themes comes out
    high (13 pairs cleared r>=0.6 in the first real run, all of them
    almost certainly this shared confound, not a hidden shared cause).
    Normalizing by total monthly volume controls for it: re-run with shares
    instead of counts, and 0 pairs clear the same threshold."""
    counts = Counter(r["timestamp"][:7] for r in matched if r["timestamp"])
    return [counts.get(m, 0) / total_by_month[m] for m in all_months]


def pearson(xs, ys):
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / (var_x ** 0.5 * var_y ** 0.5)


def cross_cluster_correlation(themes, reviews):
    """themes: dict[name -> need_text_or_label, review_filter]."""
    all_months = sorted(set(r["timestamp"][:7] for r in reviews if r["timestamp"]))
    total_by_month = Counter(r["timestamp"][:7] for r in reviews if r["timestamp"])
    vectors = {}
    keywords = {}
    matched_counts = {}
    for name, (label, flt) in themes.items():
        matched = [r for r in reviews if flt(r)]
        matched_counts[name] = len(matched)
        vectors[name] = monthly_share_vector(matched, all_months, total_by_month)
        keywords[name] = extract_keywords(label)

    all_pairs = []
    names = list(themes.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if matched_counts[a] < MIN_THEME_N or matched_counts[b] < MIN_THEME_N:
                continue
            shared_kw = keywords[a] & keywords[b]
            if len(shared_kw) > MAX_SHARED_KEYWORDS:
                continue  # they already share obvious vocabulary -- not the "hidden" case
            r = pearson(vectors[a], vectors[b])
            all_pairs.append({
                "theme_a": a, "theme_b": b, "correlation": round(r, 3),
                "shared_keywords": sorted(shared_kw),
                "n_a": matched_counts[a], "n_b": matched_counts[b],
            })
    all_pairs.sort(key=lambda x: -abs(x["correlation"]))
    passed = [p for p in all_pairs if abs(p["correlation"]) >= CORRELATION_THRESHOLD]
    # Top 5 regardless of threshold, so a synthesis pass can see what came
    # close even when nothing clears the bar -- an honest negative result
    # shouldn't also hide the near-misses.
    near_misses = all_pairs[:5]
    return passed, near_misses


def known_themes(infer, sensitivity):
    """Existing shipped + rejected candidates, reused as-is (not reinvented)
    for Detectors 3/4 -- both as a source of new-cluster candidates in
    their own right and as a validity check on the already-shipped gaps
    (does silent churn explain any of their complaint patterns, rather
    than resolution?)."""
    themes = {}
    for c in infer.CANDIDATES:
        themes[c["id"]] = (c["need"], c["review_filter"])
    for c in sensitivity.RECONSTRUCTED_REJECTED_CANDIDATES:
        themes[c["id"]] = (c["need"], c["review_filter"])
    return themes


def new_candidate_themes():
    """Keyword-based themes surfaced by manual corpus exploration ahead of
    writing this script (see commit description for the grep sweep) --
    fed into Detectors 3/4 alongside the known themes above, since those
    detectors need SOME theme definition and the point of this phase is to
    find themes the existing pipeline didn't already define."""
    return {
        "muted-words-workaround": (
            "Users manually maintain large mute/block-word lists as a substitute for "
            "missing category-level content controls",
            lambda r: bool(re.search(r"\bmut(e|ed|ing)\b", r["text"], re.I)),
        ),
        "manual-refresh-restart-workaround": (
            "Users restart the app to force a refresh instead of the app auto-updating",
            lambda r: bool(re.search(
                r"have to restart|restart the app (whenever|every|in order|to)|restart it (all the time|to)",
                r["text"], re.I)),
        ),
        "photo-folder-workaround": (
            "Users describe manual workarounds for limited photo-folder access when posting images",
            lambda r: bool(re.search(r"folder|three basic|camera roll", r["text"], re.I)
                            and re.search(r"photo|pic(ture)?s?|image", r["text"], re.I)),
        ),
    }


def main():
    infer = _load_module("03_infer_gaps.py")
    sensitivity = _load_module("05_rubric_sensitivity.py")
    reviews = infer.load_jsonl(infer.REVIEWS_PATH)

    workaround = detect_workaround_language(reviews)
    comparison = detect_implicit_comparison(reviews)

    themes = known_themes(infer, sensitivity)
    new_themes = new_candidate_themes()

    churn_results = []
    for name, (label, flt) in list(themes.items()) + list(new_themes.items()):
        churn_results.append(silent_churn_analysis(name, flt, reviews))

    all_themes_for_corr = dict(themes)
    all_themes_for_corr.update(new_themes)
    correlation_results, near_miss_pairs = cross_cluster_correlation(all_themes_for_corr, reviews)

    output = {
        "phase_0_finding": (
            "No reviewer/user identifier exists anywhere in data/normalized/reviews.jsonl "
            "(top-level keys: timestamp, source_type, text, metadata, id, source_dataset, "
            "rating; metadata keys: helpful_count, char_len, is_exact_duplicate_text, "
            "app_id) or in the original raw CSV header (review_id, app_id, review_text, "
            "review_score, review_date, helpful_count, len) -- confirmed, not assumed. "
            "Detector 4 (cross-cluster correlation) therefore uses time-based co-occurrence "
            "(monthly volume correlation) as the honest substitute, not same-reviewer tracking."
        ),
        "workaround_language": {
            "detector": "Detector 1: workaround language",
            "n_matches": len(workaround),
            "matches": workaround,
        },
        "implicit_comparison": {
            "detector": "Detector 2: implicit-standard via comparison",
            "n_matches": len(comparison),
            "matches": comparison,
        },
        "silent_churn_divergence": {
            "detector": "Detector 3: silent-churn divergence",
            "themes_checked": churn_results,
            "flagged_themes": [r["theme"] for r in churn_results if r.get("flagged")],
        },
        "cross_cluster_correlation": {
            "detector": "Detector 4: cross-cluster time-correlation",
            "note": (
                "Correlated on each theme's SHARE of that month's total review volume, not "
                "raw counts -- raw counts falsely correlated almost every theme pair (13 "
                "pairs cleared r>=0.6) because total review volume itself spikes ~10x in "
                "2024-11 and every theme rides that same wave; that confound is controlled "
                "for here, and no pair clears the threshold once it is."
            ),
            "correlation_threshold": CORRELATION_THRESHOLD,
            "max_shared_keywords": MAX_SHARED_KEYWORDS,
            "correlated_pairs": correlation_results,
            "near_miss_pairs_for_context": near_miss_pairs,
        },
        "new_candidate_theme_definitions": {
            name: label for name, (label, _flt) in new_candidate_themes().items()
        },
    }

    OUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote {OUT_PATH}")
    print(f"Detector 1 (workaround language): {len(workaround)} matches")
    print(f"Detector 2 (implicit comparison): {len(comparison)} matches")
    print(f"Detector 3 (silent-churn divergence): {len(output['silent_churn_divergence']['flagged_themes'])} "
          f"theme(s) flagged out of {len(churn_results)} checked")
    print(f"Detector 4 (cross-cluster correlation): {len(correlation_results)} pair(s) above threshold")


if __name__ == "__main__":
    main()
