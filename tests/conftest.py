from datetime import datetime, timezone

import pytest

from history_assistant.db import Database
from history_assistant.seed import seed
from history_assistant.service import HistoryService


class FixedClock:
    def __init__(self):
        self.value = datetime(2026, 10, 12, 18, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.value


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "history.sqlite3")
    seed(database)
    return database


@pytest.fixture
def clock():
    return FixedClock()


@pytest.fixture
def service(db, clock):
    return HistoryService(db, clock=clock)


def pytest_addoption(parser):
    parser.addoption("--run-live-model", action="store_true", default=False)


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-live-model"):
        for item in items:
            if "live_model" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="Real-model inference is explicit opt-in; not authorized for this run."))
