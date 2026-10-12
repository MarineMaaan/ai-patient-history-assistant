PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS patients (
    id TEXT PRIMARY KEY, label TEXT NOT NULL, interval_days INTEGER NOT NULL DEFAULT 7,
    last_checkin TEXT, next_due TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
    CHECK (interval_days BETWEEN 1 AND 365)
);
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id),
    kind TEXT NOT NULL CHECK(kind IN ('interview','checkin','correction')),
    started_at TEXT NOT NULL, completed_at TEXT, token TEXT NOT NULL,
    UNIQUE(id,patient_id), UNIQUE(patient_id,token)
);
CREATE TABLE IF NOT EXISTS clinician_questions (
    id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id),
    clinician TEXT NOT NULL, question TEXT NOT NULL, recorded_at TEXT NOT NULL,
    outcome TEXT NOT NULL DEFAULT 'pending', token TEXT NOT NULL,
    UNIQUE(id,patient_id), UNIQUE(patient_id,token)
);
CREATE TABLE IF NOT EXISTS followups (
    id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id),
    gap_key TEXT NOT NULL, topic TEXT NOT NULL, question TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('proposed','approved','asked','answered','declined','dismissed')),
    resolved INTEGER NOT NULL DEFAULT 0 CHECK(resolved IN (0,1)),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, review_note TEXT NOT NULL DEFAULT '',
    UNIQUE(id,patient_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_gap ON followups(patient_id,gap_key)
    WHERE resolved=0 AND state NOT IN ('declined','dismissed');
CREATE TABLE IF NOT EXISTS question_followups (
    question_id TEXT NOT NULL, followup_id TEXT NOT NULL, patient_id TEXT NOT NULL,
    PRIMARY KEY(question_id,followup_id),
    FOREIGN KEY(question_id,patient_id) REFERENCES clinician_questions(id,patient_id),
    FOREIGN KEY(followup_id,patient_id) REFERENCES followups(id,patient_id)
);
CREATE TABLE IF NOT EXISTS exchanges (
    id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, session_id TEXT NOT NULL,
    question TEXT NOT NULL, answer TEXT NOT NULL,
    answer_state TEXT NOT NULL CHECK(answer_state IN ('answered','unknown','declined','skipped','uncertain')),
    respondent TEXT NOT NULL, origin TEXT NOT NULL, topic TEXT NOT NULL,
    recorded_at TEXT NOT NULL, event_wording TEXT NOT NULL DEFAULT '',
    event_precision TEXT NOT NULL DEFAULT 'unknown', normalized_event_date TEXT,
    related_to TEXT, relation TEXT CHECK(relation IN ('correction','change','conflict','clarification')),
    followup_id TEXT, token TEXT NOT NULL, payload_hash TEXT NOT NULL,
    UNIQUE(id,patient_id), UNIQUE(patient_id,token),
    FOREIGN KEY(session_id,patient_id) REFERENCES sessions(id,patient_id),
    FOREIGN KEY(related_to,patient_id) REFERENCES exchanges(id,patient_id),
    FOREIGN KEY(followup_id,patient_id) REFERENCES followups(id,patient_id)
);
CREATE TRIGGER IF NOT EXISTS immutable_exchange_update BEFORE UPDATE ON exchanges
BEGIN SELECT RAISE(ABORT, 'Original exchanges are immutable; append a correction.'); END;
CREATE TRIGGER IF NOT EXISTS immutable_exchange_delete BEFORE DELETE ON exchanges
BEGIN SELECT RAISE(ABORT, 'Original exchanges are immutable; use confirmed demo reset.'); END;
CREATE TABLE IF NOT EXISTS outputs (
    id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id), question_id TEXT,
    kind TEXT NOT NULL, payload TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
    prompt_version TEXT NOT NULL, generated_at TEXT NOT NULL, generation_ms INTEGER NOT NULL,
    revision INTEGER NOT NULL, search_info TEXT NOT NULL, error TEXT,
    UNIQUE(id,patient_id), UNIQUE(question_id),
    FOREIGN KEY(question_id,patient_id) REFERENCES clinician_questions(id,patient_id)
);
CREATE TABLE IF NOT EXISTS output_sources (
    output_id TEXT NOT NULL, exchange_id TEXT NOT NULL, patient_id TEXT NOT NULL,
    PRIMARY KEY(output_id,exchange_id),
    FOREIGN KEY(output_id,patient_id) REFERENCES outputs(id,patient_id),
    FOREIGN KEY(exchange_id,patient_id) REFERENCES exchanges(id,patient_id)
);
CREATE TABLE IF NOT EXISTS activity (
    id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id),
    action TEXT NOT NULL, target_id TEXT NOT NULL, recorded_at TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT ''
);
