"""Short-lived SQLite connections, scoped reads, and atomic append operations."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator
from uuid import uuid4


def new_id() -> str:
    return str(uuid4())


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def patients(self) -> list[dict]:
        with self.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM patients ORDER BY id")]

    def patient(self, patient_id: str) -> dict:
        with self.connect() as conn:
            return self.require(conn, "patients", patient_id, patient_id)

    @staticmethod
    def require(conn, table: str, record_id: str, patient_id: str) -> dict:
        # Table names are an internal allowlist; all user values are parameters.
        allowed = {"patients", "sessions", "exchanges", "followups", "outputs", "clinician_questions"}
        if table not in allowed:
            raise ValueError("Unsupported record type")
        field = "id" if table == "patients" else "patient_id"
        row = conn.execute(f"SELECT * FROM {table} WHERE id=? AND {field}=?", (record_id, patient_id)).fetchone()
        if row is None:
            raise ValueError("Record not found for the selected patient")
        return dict(row)

    def get(self, table: str, record_id: str, patient_id: str) -> dict:
        with self.connect() as conn:
            return self.require(conn, table, record_id, patient_id)

    def records(self, table: str, patient_id: str) -> list[dict]:
        columns = {
            "exchanges": "recorded_at", "followups": "created_at", "outputs": "generated_at",
            "activity": "recorded_at", "clinician_questions": "recorded_at", "sessions": "started_at",
        }
        if table not in columns:
            raise ValueError("Unsupported record type")
        with self.connect() as conn:
            self.require(conn, "patients", patient_id, patient_id)
            return [dict(r) for r in conn.execute(
                f"SELECT * FROM {table} WHERE patient_id=? ORDER BY {columns[table]},id", (patient_id,))]

    def sources(self, patient_id: str, output_id: str) -> list[dict]:
        with self.connect() as conn:
            self.require(conn, "outputs", output_id, patient_id)
            return [dict(r) for r in conn.execute(
                "SELECT e.* FROM output_sources s JOIN exchanges e ON e.id=s.exchange_id AND e.patient_id=s.patient_id "
                "WHERE s.patient_id=? AND s.output_id=? ORDER BY e.recorded_at,e.id", (patient_id, output_id))]

    def original_snapshot(self, patient_id: str) -> tuple[list[dict], int]:
        """Read revision and evidence in the same transaction before inference."""
        with self.connect() as conn:
            conn.execute("BEGIN")
            patient = self.require(conn, "patients", patient_id, patient_id)
            rows = [dict(r) for r in conn.execute("SELECT * FROM exchanges WHERE patient_id=? ORDER BY recorded_at,id", (patient_id,))]
            return rows, patient["revision"]

    def linked_questions(self, patient_id: str, followup_id: str) -> list[dict]:
        with self.connect() as conn:
            self.require(conn, "followups", followup_id, patient_id)
            return [dict(r) for r in conn.execute(
                "SELECT q.* FROM question_followups l JOIN clinician_questions q ON q.id=l.question_id "
                "AND q.patient_id=l.patient_id WHERE l.patient_id=? AND l.followup_id=?", (patient_id, followup_id))]

    @staticmethod
    def event(conn, patient_id: str, action: str, target: str, now: str, detail: str = ""):
        # Logs contain identifiers/state transitions, not duplicated patient text.
        conn.execute("INSERT INTO activity VALUES(?,?,?,?,?,?)", (new_id(), patient_id, action, target, now, detail))
