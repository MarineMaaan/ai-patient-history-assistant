"""Ignored project-local configuration. Offline mode is the default."""
import os
from pathlib import Path
import tomllib

from .seed import DEFAULT_DB, ROOT


def load_config() -> dict:
    path = ROOT / "local" / "config.toml"
    defaults = {"mode": "offline", "ollama_endpoint": "http://127.0.0.1:11434", "ollama_model": "", "timeout_seconds": 30}
    if path.exists():
        defaults.update(tomllib.loads(path.read_text(encoding="utf-8")))
    return defaults


def db_path() -> Path:
    # This environment override is for isolated tests/demo runs, never model input.
    return Path(os.environ.get("HISTORY_DB_PATH", str(DEFAULT_DB)))
