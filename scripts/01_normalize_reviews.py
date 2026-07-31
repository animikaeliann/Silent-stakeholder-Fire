"""
Normalize data/raw/bluesky_reviews.csv into the schema locked in SPEC.md §2.

Rule from SPEC.md: every raw record produces exactly one normalized record.
No silent drops. Anything filtered (dedup, empty text, etc.) gets logged
to logs/filtered.jsonl with a reason, not just discarded.

Usage: python 01_normalize_reviews.py
"""
import csv
import json
import hashlib
from pathlib import Path
from datetime import datetime

RAW_PATH = Path("data/raw/bluesky_reviews.csv")
OUT_PATH = Path("data/normalized/reviews.jsonl")
FILTERED_LOG = Path("logs/filtered.jsonl")
DATASET_NAME = "bluesky_reviews_upload"  # user-provided CSV, app_id=174

def normalize():
    normalized = []
    filtered = []
    seen_text_hashes = {}  # hash -> first id that had this exact text

    with open(RAW_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_id = row["review_id"].strip()
            text = row["review_text"].strip()
            norm_id = f"review-play-{raw_id.replace('RV-', '')}"

            if not text:
                filtered.append({
                    "raw_id": raw_id, "reason": "empty_text_after_strip"
                })
                continue

            text_hash = hashlib.md5(text.lower().encode()).hexdigest()
            if text_hash in seen_text_hashes:
                filtered.append({
                    "raw_id": raw_id,
                    "reason": "exact_duplicate_text",
                    "duplicate_of": seen_text_hashes[text_hash],
                    "text_preview": text[:80],
                })
                is_duplicate = True
            else:
                seen_text_hashes[text_hash] = norm_id
                is_duplicate = False

            try:
                ts = datetime.strptime(row["review_date"].strip(), "%Y-%m-%d").isoformat()
            except ValueError:
                ts = None
                filtered.append({"raw_id": raw_id, "reason": "unparseable_date", "raw_value": row["review_date"]})

            normalized.append({
                "id": norm_id,
                "source_type": "review",
                "source_dataset": DATASET_NAME,
                "text": text,
                "timestamp": ts,
                "rating": int(row["review_score"]),
                "metadata": {
                    "helpful_count": int(row["helpful_count"]),
                    "char_len": int(row["len"]),
                    "app_id": row["app_id"],
                    "is_exact_duplicate_text": is_duplicate,
                },
            })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        for rec in normalized:
            f.write(json.dumps(rec) + "\n")

    FILTERED_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(FILTERED_LOG, "a") as f:
        for rec in filtered:
            f.write(json.dumps({"stage": "normalize_reviews", **rec}) + "\n")

    print(f"Normalized: {len(normalized)} records -> {OUT_PATH}")
    print(f"Filtered/flagged: {len(filtered)} records -> {FILTERED_LOG}")
    dup_count = sum(1 for r in normalized if r["metadata"]["is_exact_duplicate_text"])
    print(f"  of which exact-duplicate-text (kept, tagged): {dup_count}")

if __name__ == "__main__":
    normalize()
