"""Explicit synthetic fixtures, separate from ignored runtime data."""
from datetime import datetime, timedelta
import json
from pathlib import Path

from .clock import stamp, utc_now
from .db import Database
from .models import Submission
from .service import HistoryService

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "local" / "history.sqlite3"
CONFIRMATION = "RESET SYNTHETIC DATA"


def seed(db: Database):
    fixtures = json.loads((ROOT / "fixtures" / "synthetic_patients.json").read_text(encoding="utf-8"))
    for p in fixtures["patients"]:
        with db.connect() as conn:
            conn.execute("INSERT OR IGNORE INTO patients(id,label,next_due) VALUES(?,?,?)",
                         (p["id"], p["label"], stamp(utc_now() + timedelta(days=7))))
        links = {}
        for session in p["sessions"]:
            clock = lambda value=session["recorded_at"]: datetime.fromisoformat(value)
            service = HistoryService(db, clock=clock)
            sid = service.start_session(p["id"], "interview", "seed-" + session["key"])
            for e in session["exchanges"]:
                existing = next((r for r in db.records("exchanges", p["id"]) if r["token"] == "seed-" + e["key"]), None)
                if existing:
                    links[e["key"]] = existing["id"]
                    continue
                data = {k: v for k, v in e.items() if k not in {"key", "related_key"}}
                if e.get("related_key"):
                    data["related_to"] = links[e["related_key"]]
                sub = Submission(**data, origin="seed", respondent="synthetic-patient:" + p["id"])
                links[e["key"]] = service.submit(p["id"], sid, sub, "seed-" + e["key"])["id"]
            service.finish_session(p["id"], sid)


def reset(path: Path, confirmation: str, local_root: Path | None = None):
    """Delete only the named demo DB and exact sidecars after typed confirmation.

    The resolved containment check also refuses links escaping the local directory.
    Stop Streamlit before resetting, especially on Windows with open handles.
    """
    root = (local_root or ROOT / "local").resolve()
    target = Path(path).resolve()
    if confirmation != CONFIRMATION:
        raise ValueError("Reset requires the exact explicit confirmation phrase")
    if not target.is_relative_to(root) or target.suffix != ".sqlite3":
        raise ValueError("Reset target must be a .sqlite3 file inside the local data directory")
    targets = [target] + [Path(str(target) + suffix) for suffix in ("-wal", "-shm", "-journal")]
    for item in targets:
        if not item.resolve().is_relative_to(root):
            raise ValueError("SQLite sidecar path escaped the local data directory")
    for item in targets:
        item.unlink(missing_ok=True)
    seed(Database(target))
