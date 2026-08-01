-- Schema for data/gaps.db -- a queryable, additive sync target for the
-- pipeline's existing output/*.json(l) files. The JSON/JSONL files remain
-- the pipeline's authoritative write target; scripts still write those
-- first, exactly as before this phase. This database is populated by
-- scripts/17_sync_to_db.py, which reads those files as they exist on disk
-- and reloads this database from scratch every run (idempotent by full
-- reload, not upsert -- see that script's docstring).
--
-- Table count is larger than the phase brief's named list (gaps, evidence,
-- rejected_candidates, team_routing, notifications, stability_scores,
-- adversarial_verification_results) because several of those source JSON
-- fields are themselves one-to-many lists (roadmap_refs, cc_teams,
-- cc_addresses, supporting_evidence_ids, adversarial concerns). Storing a
-- list as a JSON-text blob column would violate "proper foreign keys, not
-- denormalized blobs, this should support real joins" -- so each list gets
-- its own linked table instead: roadmap_refs, rejected_evidence,
-- team_routing_cc, notification_cc, adversarial_concerns.
--
-- Foreign keys are declared but SQLite does not enforce them unless the
-- connection runs `PRAGMA foreign_keys = ON` -- scripts/17_sync_to_db.py
-- and backend/app.py both set this explicitly.

DROP TABLE IF EXISTS adversarial_concerns;
DROP TABLE IF EXISTS adversarial_verification_results;
DROP TABLE IF EXISTS stability_scores;
DROP TABLE IF EXISTS notification_cc;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS team_routing_cc;
DROP TABLE IF EXISTS team_routing;
DROP TABLE IF EXISTS rejected_evidence;
DROP TABLE IF EXISTS rejected_candidates;
DROP TABLE IF EXISTS roadmap_refs;
DROP TABLE IF EXISTS evidence;
DROP TABLE IF EXISTS gaps;

-- One row per shipped gap. `rank` is the natural key: it's already the
-- join key output/team_routing.json and output/team_notifications/*.json
-- use (as "gap_rank"), so reusing it here (rather than inventing a
-- surrogate id) keeps this schema's join key identical to the one the
-- rest of the pipeline already relies on.
--
-- `shipped_at`: gaps.json itself carries no per-gap timestamp field (SPEC.md
-- §3's gap object contract has no timestamp), so this is derived from
-- output/gaps.json's own file mtime at sync time -- the best real, verifiable
-- signal available for "when this gap version was written," not a
-- per-gap event time and not invented data.
CREATE TABLE gaps (
    rank                              INTEGER PRIMARY KEY,
    need                              TEXT NOT NULL,
    confidence                        REAL NOT NULL,
    confidence_justification          TEXT NOT NULL,
    verdict                           TEXT NOT NULL,
    verdict_justification             TEXT NOT NULL,
    rejected_alternative_explanations TEXT,
    shipped_at                        TEXT NOT NULL
);

-- One row per evidence entry (SPEC.md §3: >= 2 entries, >= 2 distinct
-- source_types per gap, enforced upstream by 03_infer_gaps.py -- not
-- re-enforced here, this is a read layer).
CREATE TABLE evidence (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    gap_rank              INTEGER NOT NULL REFERENCES gaps(rank),
    evidence_id           TEXT NOT NULL,   -- e.g. "review-play-04353", "github-issue-6264"
    excerpt_or_paraphrase TEXT NOT NULL,
    weight                TEXT NOT NULL CHECK (weight IN ('primary', 'corroborating'))
);
CREATE INDEX idx_evidence_gap_rank ON evidence(gap_rank);

-- One row per roadmap_refs entry (not named in the phase brief's table
-- list, but the same list-becomes-a-blob problem as evidence -- see the
-- header comment).
CREATE TABLE roadmap_refs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    gap_rank   INTEGER NOT NULL REFERENCES gaps(rank),
    roadmap_id TEXT NOT NULL,   -- e.g. "github-issue-6264"
    relation   TEXT NOT NULL
);
CREATE INDEX idx_roadmap_refs_gap_rank ON roadmap_refs(gap_rank);

-- One row per rejected candidate (output/rejected_candidates.jsonl). No
-- natural key exists in that file (no "id"/"rank" field) -- surrogate
-- autoincrement id.
CREATE TABLE rejected_candidates (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    need TEXT NOT NULL,
    reason TEXT NOT NULL
);

-- One row per supporting_evidence_id (rejected_candidates.jsonl's version
-- of evidence -- just a list of id strings, no excerpt/weight, so it's a
-- thinner table than `evidence` above, not a merge into it).
CREATE TABLE rejected_evidence (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    rejected_candidate_id  INTEGER NOT NULL REFERENCES rejected_candidates(id),
    evidence_id            TEXT NOT NULL
);
CREATE INDEX idx_rejected_evidence_candidate ON rejected_evidence(rejected_candidate_id);

-- One row per gap (1:1 with gaps, output/team_routing.json is one entry
-- per shipped gap right now).
CREATE TABLE team_routing (
    gap_rank   INTEGER PRIMARY KEY REFERENCES gaps(rank),
    team       TEXT NOT NULL,
    signal_used TEXT NOT NULL,
    reasoning  TEXT NOT NULL
);

-- cc_teams is a list in the source JSON (empty for gaps 1/3, non-empty for
-- gaps 2/4 in the real data -- verified, not assumed always-empty).
CREATE TABLE team_routing_cc (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    gap_rank INTEGER NOT NULL REFERENCES gaps(rank),
    cc_team  TEXT NOT NULL
);
CREATE INDEX idx_team_routing_cc_gap_rank ON team_routing_cc(gap_rank);

-- One row per gap (1:1, output/team_notifications/gap_{rank}_{team}.json).
-- `status`: no file on disk records whether a notification was actually
-- sent -- scripts/09_send_notifications.py's dry-run mode "prints...sends
-- nothing, writes nothing" (its own docstring), and real-send mode talks
-- to live SMTP with no persisted record either. Every row synced here is
-- 'drafted' because that's the only state this sync script can verify
-- from disk -- not a claim that nothing was ever sent.
CREATE TABLE notifications (
    gap_rank            INTEGER PRIMARY KEY REFERENCES gaps(rank),
    team                TEXT NOT NULL,
    to_address          TEXT NOT NULL,
    subject             TEXT NOT NULL,
    suggested_next_step TEXT,
    routing_reasoning   TEXT,
    body_text           TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'drafted' CHECK (status IN ('drafted', 'dry_run', 'sent'))
);

-- cc_addresses is a list in the source JSON (non-empty for gaps 2/4 --
-- verified).
CREATE TABLE notification_cc (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    gap_rank   INTEGER NOT NULL REFERENCES gaps(rank),
    cc_address TEXT NOT NULL
);
CREATE INDEX idx_notification_cc_gap_rank ON notification_cc(gap_rank);

-- One row per shipped gap, combining bootstrap resampling stability
-- (output/bootstrap_stability.md) and rubric-weight sensitivity
-- (output/rubric_sensitivity.md) -- both markdown-table reports, not JSON,
-- parsed by scripts/17_sync_to_db.py the same way scripts/12 and
-- scripts/15 already parse these same report files.
CREATE TABLE stability_scores (
    gap_rank                          INTEGER PRIMARY KEY REFERENCES gaps(rank),
    bootstrap_stable_count            INTEGER,
    bootstrap_total_resamples         INTEGER,
    bootstrap_avg_overlap_fraction    REAL,
    bootstrap_avg_centroid_sim        REAL,
    sensitivity_baseline_confidence   REAL,
    sensitivity_min_confidence        REAL,
    sensitivity_max_confidence        REAL
);

-- One row per shipped gap, from output/adversarial_verification.md
-- (markdown, parsed like stability_scores above).
CREATE TABLE adversarial_verification_results (
    gap_rank           INTEGER PRIMARY KEY REFERENCES gaps(rank),
    tail_silence_days  INTEGER,
    survived_verdict   TEXT,    -- 'YES' or 'YES_WITH_CAVEATS' (this project's only 2 observed values)
    concern_count      INTEGER
);

-- One row per concern bullet listed under a gap's adversarial section
-- (empty for gaps with 0 concerns).
CREATE TABLE adversarial_concerns (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    gap_rank     INTEGER NOT NULL REFERENCES gaps(rank),
    concern_text TEXT NOT NULL
);
CREATE INDEX idx_adversarial_concerns_gap_rank ON adversarial_concerns(gap_rank);
