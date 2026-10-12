"""Application workflows: source capture first, derived interpretation afterward."""
from datetime import datetime, timedelta
import hashlib
import json
import re
import time

from .clock import Clock, stamp, utc_now
from .db import Database, new_id
from .evidence import EvidenceError, validate_draft
from .interview import LIBRARY, addresses_gap, neutral_question, proposed_question, unsafe_request
from .models import Draft, Submission
from .prompts import PROMPT_VERSION
from .providers import OfflineProvider, Provider, ProviderError
from .retrieval import missing_detail, retrieve, topic_for

MISSING = "I found no statement addressing this in the records searched"


class HistoryService:
    def __init__(self, db: Database, provider: Provider | None = None, clock: Clock = utc_now):
        self.db, self.provider, self.clock = db, provider or OfflineProvider(), clock

    def now(self) -> str:
        return stamp(self.clock())

    def start_session(self, patient_id: str, kind: str, token: str) -> str:
        if kind not in {"interview", "checkin", "correction"} or not token or len(token) > 200:
            raise ValueError("Invalid session")
        with self.db.connect() as conn:
            self.db.require(conn, "patients", patient_id, patient_id)
            prior = conn.execute("SELECT * FROM sessions WHERE patient_id=? AND token=?", (patient_id, token)).fetchone()
            if prior:
                if prior["kind"] != kind:
                    raise ValueError("Submission token reused for a different session")
                return prior["id"]
            record_id = new_id()
            conn.execute("INSERT INTO sessions VALUES(?,?,?,?,NULL,?)", (record_id, patient_id, kind, self.now(), token))
            self.db.event(conn, patient_id, "session_started", record_id, self.now(), kind)
            return record_id

    def submit(self, patient_id: str, session_id: str, submission: Submission, token: str) -> dict:
        if not token or len(token) > 200:
            raise ValueError("Invalid submission token")
        payload_hash = hashlib.sha256((session_id + submission.model_dump_json()).encode()).hexdigest()
        with self.db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute("SELECT * FROM exchanges WHERE patient_id=? AND token=?", (patient_id, token)).fetchone()
            if previous:
                if previous["payload_hash"] != payload_hash:
                    raise ValueError("Submission token reused with different content")
                return dict(previous)
            session = self.db.require(conn, "sessions", session_id, patient_id)
            if session["completed_at"]:
                raise ValueError("Session already completed")
            if submission.related_to:
                self.db.require(conn, "exchanges", submission.related_to, patient_id)
            if submission.followup_id:
                followup = self.db.require(conn, "followups", submission.followup_id, patient_id)
                if followup["state"] not in {"approved", "asked"} or followup["resolved"]:
                    raise ValueError("Follow-up is not approved and open")
                if submission.question != followup["question"] or submission.topic != followup["topic"]:
                    raise ValueError("Submitted question must match the approved question shown")
            record_id, now = new_id(), self.now()
            conn.execute(
                "INSERT INTO exchanges VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (record_id, patient_id, session_id, submission.question, submission.answer, submission.state,
                 submission.respondent, submission.origin, submission.topic, now, submission.event_wording,
                 submission.event_precision, None, submission.related_to, submission.relation, submission.followup_id,
                 token, payload_hash),
            )
            # No event-date normalization is performed. Even 'July 2025' stays
            # reported wording with month precision, never an invented day.
            conn.execute("UPDATE patients SET revision=revision+1 WHERE id=?", (patient_id,))
            if submission.followup_id:
                state = "declined" if submission.state == "declined" else (
                    "asked" if submission.state == "skipped" else "answered")
                resolved = addresses_gap(submission.topic, submission.answer, submission.state)
                conn.execute("UPDATE followups SET state=?,resolved=?,updated_at=?,review_note=? WHERE id=? AND patient_id=?",
                             (state, int(resolved), now, "narrow rules match" if resolved else "needs reviewer assessment",
                              submission.followup_id, patient_id))
                self.db.event(conn, patient_id, "followup_response", submission.followup_id, now, f"{state}; resolved={resolved}")
            self.db.event(conn, patient_id, "exchange_submitted", record_id, now, submission.state)
            return self.db.require(conn, "exchanges", record_id, patient_id)

    def queue(self, patient_id: str) -> list[dict]:
        return [r for r in self.db.records("followups", patient_id) if r["state"] in {"approved", "asked"} and not r["resolved"]]

    def next_question(self, patient_id: str, session_id: str) -> dict | None:
        session = self.db.get("sessions", session_id, patient_id)
        records = self.db.records("exchanges", patient_id)
        current = [r for r in records if r["session_id"] == session_id]
        for followup in self.queue(patient_id):
            if not any(r["followup_id"] == followup["id"] for r in current):
                return {"question": followup["question"], "topic": followup["topic"], "origin": "followup", "followup_id": followup["id"]}
        for q in LIBRARY:
            if session["kind"] == "checkin":
                eligible = q.topic == "changes" and not any(r["topic"] == "changes" for r in current)
            else:
                eligible = not any(r["topic"] == q.topic for r in records)
            if eligible:
                return {"question": q.question, "topic": q.topic, "origin": "library", "followup_id": None}
        return None

    def mark_asked(self, patient_id: str, followup_id: str):
        with self.db.connect() as conn:
            f = self.db.require(conn, "followups", followup_id, patient_id)
            if f["state"] == "approved":
                conn.execute("UPDATE followups SET state='asked',updated_at=? WHERE id=? AND patient_id=?", (self.now(), followup_id, patient_id))
                self.db.event(conn, patient_id, "followup_asked", followup_id, self.now())

    def clarification(self, patient_id: str, exchange_id: str) -> tuple[str | None, str | None]:
        last = self.db.get("exchanges", exchange_id, patient_id)
        asked = [r["question"] for r in self.db.records("exchanges", patient_id)]
        try:
            candidate = self.provider.clarify(last, asked).question
            if candidate and (not neutral_question(candidate) or candidate in asked):
                raise ProviderError("Generated clarification was unsafe or repeated; next library question remains available.")
            if candidate and topic_for(candidate) != last["topic"] and not re.search(r"date|approximate period|clarify|what.*mean", candidate, re.I):
                raise ProviderError("Generated clarification was outside the supported history scope.")
            # It is only a draft, never an exchange until explicitly submitted.
            return candidate, None
        except (ProviderError, ValueError):
            return None, "Clarification provider failed validation or was unavailable. Response saved; use the next library question."

    def finish_session(self, patient_id: str, session_id: str):
        with self.db.connect() as conn:
            session = self.db.require(conn, "sessions", session_id, patient_id)
            if session["completed_at"]:
                return
            now = self.now()
            conn.execute("UPDATE sessions SET completed_at=? WHERE id=? AND patient_id=?", (now, session_id, patient_id))
            if session["kind"] == "checkin":
                patient = self.db.require(conn, "patients", patient_id, patient_id)
                due = stamp(self.clock() + timedelta(days=patient["interval_days"]))
                conn.execute("UPDATE patients SET last_checkin=?,next_due=? WHERE id=?", (now, due, patient_id))
            self.db.event(conn, patient_id, "session_completed", session_id, now)

    def schedule(self, patient_id: str, action: str, days: int = 7):
        if not 1 <= days <= 365 or action not in {"simulate", "postpone", "interval"}:
            raise ValueError("Invalid demonstration schedule")
        with self.db.connect() as conn:
            self.db.require(conn, "patients", patient_id, patient_id)
            if action == "interval":
                conn.execute("UPDATE patients SET interval_days=? WHERE id=?", (days, patient_id))
            else:
                due = stamp(self.clock() + (timedelta(seconds=-1) if action == "simulate" else timedelta(days=days)))
                conn.execute("UPDATE patients SET next_due=? WHERE id=?", (due, patient_id))
            self.db.event(conn, patient_id, "schedule_" + action, patient_id, self.now())

    def is_due(self, patient_id: str) -> bool:
        return datetime.fromisoformat(self.db.patient(patient_id)["next_due"]) <= self.clock()

    def review_followup(self, patient_id: str, followup_id: str, action: str, edited: str = "", note: str = ""):
        with self.db.connect() as conn:
            f = self.db.require(conn, "followups", followup_id, patient_id)
            if action == "approve":
                if f["state"] != "proposed":
                    raise ValueError("Only proposed questions can be approved")
                text = edited or f["question"]
                if not neutral_question(text):
                    raise ValueError("Use one neutral history question without diagnostic or treatment language")
                conn.execute("UPDATE followups SET state='approved',question=?,updated_at=? WHERE id=? AND patient_id=?", (text, self.now(), followup_id, patient_id))
            elif action == "dismiss":
                conn.execute("UPDATE followups SET state='dismissed',updated_at=? WHERE id=? AND patient_id=?", (self.now(), followup_id, patient_id))
            elif action in {"resolve", "requeue"}:
                if f["state"] != "answered" or f["resolved"]:
                    raise ValueError("Only an unresolved answered proposal can be reviewed")
                if action == "resolve":
                    answers = [r for r in self.db.records("exchanges", patient_id) if r["followup_id"] == followup_id and r["answer_state"] == "answered"]
                    if not answers or not note.strip() or len(note) > 1000:
                        raise ValueError("Resolution requires a substantive answer and a reviewer explanation")
                conn.execute("UPDATE followups SET state=?,resolved=?,review_note=?,updated_at=? WHERE id=? AND patient_id=?",
                             ("answered" if action == "resolve" else "approved", int(action == "resolve"), note,
                              self.now(), followup_id, patient_id))
            else:
                raise ValueError("Unsupported review action")
            self.db.event(conn, patient_id, "followup_" + action, followup_id, self.now())

    def _persist_output(self, patient_id: str, question_id: str | None, kind: str, draft: Draft, search,
                        provider: str, model: str, elapsed: int, error: str | None, propose: bool = True) -> dict:
        with self.db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if question_id:
                prior = conn.execute("SELECT * FROM outputs WHERE patient_id=? AND question_id=?", (patient_id, question_id)).fetchone()
                if prior:
                    return dict(prior)
            record_id, now = new_id(), self.now()
            revision = search.info["revision"]
            conn.execute("INSERT INTO outputs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                record_id, patient_id, question_id, kind, draft.model_dump_json(), provider, model,
                PROMPT_VERSION, now, elapsed, revision, json.dumps(search.info), error))
            # All context sources are preserved, including unknown/declined exchanges
            # and correction ancestors. Only validated claims are rendered as claims.
            for r in search.evidence:
                conn.execute("INSERT INTO output_sources VALUES(?,?,?)", (record_id, r["id"], patient_id))
            if question_id:
                conn.execute("UPDATE clinician_questions SET outcome=? WHERE id=? AND patient_id=?", (draft.outcome, question_id, patient_id))
                if propose and draft.outcome != "supported":
                    q = self.db.require(conn, "clinician_questions", question_id, patient_id)
                    topic = topic_for(q["question"]) or "other"
                    detail = search.info.get("missing_detail")
                    key = topic if topic != "other" else hashlib.sha256(q["question"].lower().strip().encode()).hexdigest()
                    if detail:
                        key += ":" + detail
                    f = conn.execute("SELECT * FROM followups WHERE patient_id=? AND gap_key=? AND resolved=0 AND state NOT IN ('dismissed','declined')", (patient_id, key)).fetchone()
                    if f:
                        followup_id = f["id"]
                    else:
                        followup_id = new_id()
                        conn.execute("INSERT INTO followups VALUES(?,?,?,?,?,'proposed',0,?,?,?)", (
                            followup_id, patient_id, key, topic, proposed_question(topic, detail), now, now, "missing or insufficient source evidence"))
                        self.db.event(conn, patient_id, "followup_proposed", followup_id, now)
                    conn.execute("INSERT OR IGNORE INTO question_followups VALUES(?,?,?)", (question_id, followup_id, patient_id))
            self.db.event(conn, patient_id, "output_created", record_id, now, kind)
            return self.db.require(conn, "outputs", record_id, patient_id)

    def query(self, patient_id: str, question: str, clinician: str, token: str) -> dict:
        if not question.strip() or len(question) > 1000 or not clinician.strip() or len(clinician) > 100 or not token or len(token) > 200:
            raise ValueError("Question/identity/token exceeds the input limits or is empty")
        with self.db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.db.require(conn, "patients", patient_id, patient_id)
            q = conn.execute("SELECT * FROM clinician_questions WHERE patient_id=? AND token=?", (patient_id, token)).fetchone()
            if q:
                if q["question"] != question or q["clinician"] != clinician:
                    raise ValueError("Question token reused with different content")
                question_id = q["id"]
                prior = conn.execute("SELECT * FROM outputs WHERE question_id=? AND patient_id=?", (question_id, patient_id)).fetchone()
                if prior:
                    return dict(prior)
            else:
                question_id = new_id()
                conn.execute("INSERT INTO clinician_questions VALUES(?,?,?,?,?,'pending',?)", (question_id, patient_id, clinician, question, self.now(), token))
                self.db.event(conn, patient_id, "clinician_question", question_id, self.now())
        return self._generate(patient_id, question, question_id, "clinician_answer")

    def summary(self, patient_id: str) -> dict:
        return self._generate(patient_id, "Summarize the recorded history", None, "history_summary")

    def _generate(self, patient_id: str, question: str, question_id: str | None, kind: str) -> dict:
        records, revision = self.db.original_snapshot(patient_id)
        search = retrieve(records, question)
        search.info["revision"] = revision
        start = time.monotonic()
        error, provider, model = None, self.provider.name, self.provider.model
        blocked = kind == "clinician_answer" and unsafe_request(question)
        if blocked:
            # Do not automatically turn a loaded request into a patient interview.
            search.evidence = []
            draft = Draft(outcome="missing")
            error = "Outside history-retrieval scope. No diagnostic, treatment, consent, or instruction-following response generated."
            provider, model = "Application scope guard", "none"
        elif search.info["limited"]:
            draft = Draft(outcome="uncertain", uncertainty=["limited_search", "patient_report_only"])
            error = "Relevant context exceeds the configured limit. Original exchanges are available; no generated conclusion."
            provider, model = "Application context guard", "none"
        else:
            try:
                draft = validate_draft(self.provider.answer(question, search), patient_id, question, search)
                detail = missing_detail(question, search.evidence) if kind == "clinician_answer" else None
                search.info["missing_detail"] = detail
                if detail:
                    draft.outcome = "uncertain" if draft.claims else "missing"
                    draft.uncertainty = sorted(set(draft.uncertainty) | {"detail_not_recorded"})
            except (ProviderError, EvidenceError, ValueError):
                # Explicit evidence-only failure, never a silent model substitution.
                draft = Draft(outcome="uncertain", uncertainty=["patient_report_only"])
                error = "Provider unavailable or evidence validation failed. No generated conclusion; review original exchanges or explicitly choose Offline mode."
        return self._persist_output(patient_id, question_id, kind, draft, search, provider, model,
                                    int((time.monotonic() - start) * 1000), error, propose=not blocked and not error)

    def approve_summary(self, patient_id: str, output_id: str):
        with self.db.connect() as conn:
            output = self.db.require(conn, "outputs", output_id, patient_id)
            if output["kind"] != "history_summary":
                raise ValueError("Select a history summary")
            if output["revision"] != self.db.require(conn, "patients", patient_id, patient_id)["revision"]:
                raise ValueError("History changed; create a fresh summary before reviewing it")
            exists = conn.execute("SELECT 1 FROM activity WHERE patient_id=? AND action='patient_summary_review' AND target_id=?", (patient_id, output_id)).fetchone()
            if not exists:
                self.db.event(conn, patient_id, "patient_summary_review", output_id, self.now(), "Patient review, not clinical verification")
