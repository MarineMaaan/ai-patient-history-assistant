from pathlib import Path

from streamlit.testing.v1 import AppTest

from history_assistant.db import Database

APP = Path(__file__).resolve().parent.parent / "app.py"


def test_ui_entire_feedback_loop_restart_and_patient_switch(tmp_path, monkeypatch):
    path = tmp_path / "ui.sqlite3"
    monkeypatch.setenv("HISTORY_DB_PATH", str(path))
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    assert any("Synthetic data only" in notice.value for notice in app.warning)
    assert any("no LLM running" in notice.value for notice in app.info)
    app.radio(key="role_selector").set_value("Simulated clinician").run()
    app.button(key="ask_history").click().run()
    assert not app.exception
    assert any("no statement addressing" in notice.value for notice in app.info)
    db = Database(path)
    f = db.records("followups", "patient-a")[0]
    app.button(key="approve_" + f["id"]).click().run()
    app.button(key="simulate_due").click().run()
    assert any("check-in is due" in notice.value for notice in app.warning)
    app.radio(key="role_selector").set_value("Patient interview").run()
    app.button(key="start_checkin").click().run()
    assert not app.exception
    app.text_area(key="patient_answer_text").set_value("I passed out once in July 2025. I don't remember the exact day.")
    app.text_input(key="event_wording").set_value("July 2025")
    app.selectbox(key="event_precision").set_value("month")
    app.button(key="save_response").click().run()
    assert not app.exception
    record = next(r for r in db.records("exchanges", "patient-a") if r["followup_id"] == f["id"])
    assert record["event_precision"] == "month" and record["normalized_event_date"] is None
    app.button(key="finish_session").click().run()
    app.radio(key="role_selector").set_value("Simulated clinician").run()
    app.button(key="ask_history").click().run()
    assert not app.exception
    assert any("I passed out once in July 2025" in text.value for text in app.text)
    app.selectbox(key="patient_selector").set_value("patient-b").run()
    assert not app.exception
    assert "answer_id" not in app.session_state
    assert not any("I passed out once" in text.value for text in app.text)
    app.button(key="ask_history").click().run()
    assert any("never fainted" in text.value for text in app.text)
    restarted = AppTest.from_file(str(APP), default_timeout=20).run()
    restarted.radio(key="role_selector").set_value("History & activity").run()
    assert not restarted.exception
    assert any("I passed out once" in text.value for text in restarted.text)


def test_ui_model_configuration_error_and_unable_to_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("HISTORY_DB_PATH", str(tmp_path / "ui.sqlite3"))
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    app.checkbox(key="unable").set_value(True).run()
    assert not any(button.key == "start_interview" for button in app.button)
    app.button(key="summary").click().run()
    assert not app.exception
    assert any("No inference of current wishes" in x.value for x in app.info)
    app.selectbox(key="mode_selector").set_value("Local Ollama").run()
    assert any("Configure an exact installed local model" in x.value for x in app.error)
    assert not app.exception
