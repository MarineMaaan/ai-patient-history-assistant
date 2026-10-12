"""Streamlit presentation only; persistence/evidence/provider rules live in services."""
import json
from uuid import uuid4

import streamlit as st

from history_assistant.config import db_path, load_config
from history_assistant.db import Database
from history_assistant.models import Submission
from history_assistant.providers import OfflineProvider, OllamaProvider, ProviderError
from history_assistant.seed import seed
from history_assistant.service import HistoryService, MISSING

NOTICE = "Educational prototype. Synthetic data only. Not for diagnosis, treatment, emergencies, or real patient records. This application is not monitored."
st.set_page_config(page_title="AI Patient History Assistant", page_icon="📋", layout="wide")
st.title("AI Patient History Assistant")
st.warning(NOTICE)
st.caption("A classroom simulation of patient-reported history. Role switching is simulated, with no production authentication.")


def exchange_view(record: dict):
    """Safe plain text prevents source/model content becoming active HTML/Markdown."""
    st.caption(f"Source {record['id']} · Recorded {record['recorded_at']} (UTC) · {record['answer_state']}")
    st.text("Question: " + record["question"])
    st.text("Patient-reported answer: " + (record["answer"] or "[No submitted answer]"))
    st.caption(f"Respondent: {record['respondent']} · Origin: {record['origin']} · Session: {record['session_id']}")
    if record["event_wording"]:
        st.text("Patient-reported event date: " + record["event_wording"])
        st.caption(f"Reported precision: {record['event_precision']}; normalized date unknown. Recording time is separate from event time.")
    if record["related_to"]:
        st.caption(f"{record['relation']} linked to source {record['related_to']}. Both statements remain available.")


def output_view(db: Database, patient_id: str, output: dict):
    st.subheader("AI-drafted summary of patient-reported information")
    st.caption(f"Historical snapshot {output['id']} · {output['generated_at']} · {output['provider']} / {output['model']} · {output['prompt_version']} · {output['generation_ms']} ms · record revision {output['revision']}")
    if output["revision"] != db.patient(patient_id)["revision"]:
        st.info("History has changed since this snapshot. Ask a fresh question or create a fresh summary for the updated record.")
    if output["error"]:
        st.error(output["error"])
    draft = json.loads(output["payload"])
    sources = db.sources(patient_id, output["id"])
    source_map = {r["id"]: r for r in sources}
    if not draft["claims"] and not output["error"]:
        st.info(MISSING + ". Non-answers below are not patient denials.")
    elif draft["claims"]:
        st.write("Supporting patient statements:")
        for claim in draft["claims"]:
            for source_id in claim["source_ids"]:
                # The model never authors displayed quotations, names, or times.
                st.text(source_map[source_id]["answer"])
                st.markdown(f"[Original exchange {source_id[:8]}](#source-{source_id})")
    st.text("Uncertainty / relationships: " + ", ".join(draft["uncertainty"]))
    st.caption("Schema validation checks structure; source IDs check identity. Neither proves interpretation or medical truth. Patient summary approval is not clinical verification.")
    info = json.loads(output["search_info"])
    st.caption(f"Searched {info['searched_count']} selected-patient original records from {info['date_start'] or 'no records'} to {info['date_end'] or 'no records'}; {info['relevant_count']} relevant/linked records. Limits: {info['max_records']} records / {info['max_chars']} estimated characters. Context limit exceeded: {info['limited']}.")
    for record in sources:
        st.subheader("Original exchange " + record["id"][:8], anchor="source-" + record["id"])
        with st.expander("Expand question, answer, and timestamp — " + record["id"][:8]):
            exchange_view(record)


def patient_screen(service: HistoryService, pid: str):
    st.subheader("Synthetic patient interview and check-in")
    unable = st.checkbox("Patient cannot currently answer — retrieval of existing statements only", key="unable")
    if unable:
        st.info("Only existing recorded statements are available. No inference of current wishes, consent, or answers on behalf of the patient.")
    else:
        if "active_session" not in st.session_state:
            cols = st.columns(2)
            if cols[0].button("Start interview", key="start_interview"):
                st.session_state.active_session = service.start_session(pid, "interview", str(uuid4()))
                st.rerun()
            if cols[1].button("Start check-in", key="start_checkin"):
                st.session_state.active_session = service.start_session(pid, "checkin", str(uuid4()))
                st.rerun()
        else:
            sid = st.session_state.active_session
            question = st.session_state.get("chosen_clarification") or service.next_question(pid, sid)
            if question:
                if question["followup_id"]:
                    service.mark_asked(pid, question["followup_id"])
                st.text(question["question"])
                st.caption("One question at a time. A draft is not a patient statement until you submit it.")
                st.session_state.setdefault("answer_token", str(uuid4()))
                with st.form("patient_answer", clear_on_submit=True):
                    answer = st.text_area("Exact patient response", max_chars=4000, key="patient_answer_text")
                    state_label = st.selectbox("Answer state", ["Answered", "Uncertain", "I don't know", "Prefer not to answer", "Skip"], key="answer_state")
                    wording = st.text_input("Patient-reported event date wording (optional)", max_chars=300, key="event_wording")
                    precision = st.selectbox("Reported event-date precision", ["unknown", "approximate", "year", "month", "day"], key="event_precision")
                    submitted = st.form_submit_button("Save exact response", key="save_response")
                if submitted:
                    state = {"Answered": "answered", "Uncertain": "uncertain", "I don't know": "unknown", "Prefer not to answer": "declined", "Skip": "skipped"}[state_label]
                    # Explicit non-answer selections can carry original free text;
                    # only an empty box gets the text of the selected response.
                    if not answer and state in {"unknown", "declined"}:
                        answer = state_label + "."
                    data = Submission(**question, answer=answer, state=state,
                                      respondent="synthetic-patient:" + pid,
                                      event_wording=wording, event_precision=precision)
                    record = service.submit(pid, sid, data, st.session_state.answer_token)
                    st.session_state.pop("answer_token", None)
                    st.session_state.pop("chosen_clarification", None)
                    st.session_state.pop("summary_id", None)
                    draft, error = service.clarification(pid, record["id"])
                    st.session_state.clarification_draft = (draft, error, record["topic"], record["id"])
                    st.session_state.flash = "Original exchange saved before optional interpretation."
                    st.rerun()
            else:
                st.info("No additional library or approved follow-up question is queued in this session.")
            if st.button("Complete session", key="finish_session"):
                service.finish_session(pid, sid)
                for key in ("active_session", "chosen_clarification", "clarification_draft", "answer_token"):
                    st.session_state.pop(key, None)
                st.session_state.flash = "Session completed. Unresolved follow-ups remain unresolved."
                st.rerun()
            clarification = st.session_state.get("clarification_draft")
            if clarification:
                draft, error, topic, related_id = clarification
                if error:
                    st.error(error)
                if draft:
                    st.text("Optional proposed clarification: " + draft)
                    if st.button("Use this clarification", key="use_clarification"):
                        st.session_state.chosen_clarification = {"question": draft, "topic": topic, "origin": "clarification", "followup_id": None, "related_to": related_id, "relation": "clarification"}
                        st.session_state.pop("clarification_draft", None)
                        st.rerun()
                    if st.button("Continue library questions", key="ignore_clarification"):
                        st.session_state.pop("clarification_draft", None)
                        st.rerun()
        with st.expander("Correct or clarify an earlier statement"):
            sources = service.db.records("exchanges", pid)
            if sources:
                with st.form("correction", clear_on_submit=True):
                    source_id = st.selectbox("Original source", [r["id"] for r in sources], format_func=lambda x: x[:8], key="correction_source")
                    relation = st.selectbox("Relationship", ["correction", "change", "conflict", "clarification"], key="relation")
                    old = next(r for r in sources if r["id"] == source_id)
                    st.text("Earlier answer: " + old["answer"])
                    text = st.text_area("New exact statement", max_chars=4000, key="correction_text")
                    correction_sent = st.form_submit_button("Append linked statement", key="save_correction")
                if correction_sent:
                    token = st.session_state.setdefault("correction_token", str(uuid4()))
                    sid = service.start_session(pid, "correction", token)
                    service.submit(pid, sid, Submission(question="What would you like to " + relation + " about your earlier statement?", answer=text, topic=old["topic"], origin="correction", respondent="synthetic-patient:" + pid, related_to=source_id, relation=relation), token)
                    service.finish_session(pid, sid)
                    st.session_state.pop("correction_token", None)
                    st.session_state.pop("summary_id", None)
                    st.session_state.flash = "Linked statement appended; the original remains unchanged."
                    st.rerun()
    if st.button("Create history summary", key="summary"):
        st.session_state.summary_id = service.summary(pid)["id"]
    if st.session_state.get("summary_id"):
        output = service.db.get("outputs", st.session_state.summary_id, pid)
        output_view(service.db, pid, output)
        if not unable and st.button("Patient reviewed this summary", key="approve_summary"):
            service.approve_summary(pid, output["id"])
            st.success("Review recorded. This does not independently verify the statements.")


def clinician_screen(service: HistoryService, pid: str):
    st.subheader("Simulated clinician — recorded-history questions")
    st.caption("Select the patient in the sidebar. Ask about previously reported history; no diagnosis, recommendations, current wishes, or consent inference.")
    with st.form("clinician_query"):
        identity = st.text_input("Simulated clinician identity", value="Classroom reviewer", max_chars=100, key="clinician_identity")
        question = st.text_area("Question about the selected patient's history", value="Has this fictional patient ever lost consciousness?", max_chars=1000, key="clinician_question")
        sent = st.form_submit_button("Ask recorded history", key="ask_history")
    if sent:
        token = st.session_state.setdefault("query_token", str(uuid4()))
        st.session_state.answer_id = service.query(pid, question, identity, token)["id"]
        st.session_state.pop("query_token", None)
    if st.session_state.get("answer_id"):
        output_view(service.db, pid, service.db.get("outputs", st.session_state.answer_id, pid))
    st.subheader("Information gaps and follow-up review")
    followups = service.db.records("followups", pid)
    if not followups:
        st.info("No follow-up proposals for this patient.")
    for f in followups:
        with st.expander(f"{f['topic']} · {f['state']} · resolved={bool(f['resolved'])} · {f['id'][:8]}"):
            st.text("Patient-facing question: " + f["question"])
            st.caption(f"Created {f['created_at']} · Updated {f['updated_at']} · {f['review_note']}")
            for q in service.db.linked_questions(pid, f["id"]):
                st.text("Linked clinician question: " + q["question"])
                st.caption(q["id"] + " · " + q["recorded_at"] + " · " + q["outcome"])
            for r in service.db.records("exchanges", pid):
                if r["followup_id"] == f["id"]:
                    exchange_view(r)
            if f["state"] == "proposed":
                with st.form("review_" + f["id"]):
                    edited = st.text_area("Edit neutral follow-up before approval", value=f["question"], max_chars=1000, key="edit_" + f["id"])
                    approve = st.form_submit_button("Approve follow-up", key="approve_" + f["id"])
                    dismiss = st.form_submit_button("Dismiss proposal", key="dismiss_" + f["id"])
                if approve or dismiss:
                    service.review_followup(pid, f["id"], "approve" if approve else "dismiss", edited=edited)
                    st.rerun()
            elif f["state"] == "answered" and not f["resolved"]:
                st.info("Response recorded; information not yet known. Review whether it addresses this gap.")
                note = st.text_input("Reviewer explanation", max_chars=1000, key="note_" + f["id"])
                if st.button("Mark gap addressed after review", key="resolve_" + f["id"]):
                    service.review_followup(pid, f["id"], "resolve", note=note)
                    st.rerun()
                if st.button("Ask again next check-in", key="requeue_" + f["id"]):
                    service.review_followup(pid, f["id"], "requeue", note=note)
                    st.rerun()
            if f["state"] in {"approved", "asked"} and st.button("Dismiss approved follow-up", key="dismiss_open_" + f["id"]):
                service.review_followup(pid, f["id"], "dismiss")
                st.rerun()


def history_screen(service: HistoryService, pid: str):
    st.subheader("History and activity timeline")
    items = []
    for table, time_field in (("exchanges", "recorded_at"), ("outputs", "generated_at"), ("activity", "recorded_at"), ("clinician_questions", "recorded_at")):
        items.extend((r[time_field], table, r) for r in service.db.records(table, pid))
    for when, kind, item in sorted(items, key=lambda x: (x[0], x[2]["id"]), reverse=True):
        with st.expander(f"{when} · {kind} · {item['id'][:8]}"):
            if kind == "exchanges":
                exchange_view(item)
            elif kind == "outputs":
                output_view(service.db, pid, item)
            elif kind == "clinician_questions":
                st.text("Simulated clinician question: " + item["question"])
                st.caption(item["clinician"] + " · " + item["outcome"])
            else:
                st.text(item["action"] + " · " + item["target_id"] + " · " + item["detail"])


def main():
    config = load_config()
    db = Database(db_path())
    seed(db)  # Idempotent explicit synthetic imports; reruns never reset user work.
    patients = db.patients()
    pid = st.sidebar.selectbox("Synthetic patient", [p["id"] for p in patients], format_func=lambda value: next(p["label"] for p in patients if p["id"] == value), key="patient_selector")
    role = st.sidebar.radio("Simulated role/view", ["Patient interview", "Simulated clinician", "History & activity"], key="role_selector")
    modes = ["Offline demo", "Local Ollama"]
    mode = st.sidebar.selectbox("Provider mode", modes, index=1 if config["mode"] == "ollama" else 0, key="mode_selector")
    context = (pid, role, mode)
    if st.session_state.get("context") != context:
        # Never reuse a prior patient's widget text, session, draft, or answer.
        for key in list(st.session_state):
            if key not in {"patient_selector", "role_selector", "mode_selector"}:
                del st.session_state[key]
        st.session_state.context = context
    if mode == "Offline demo":
        provider = OfflineProvider()
        st.info(provider.name)
    else:
        st.info("Local Ollama mode selected. No model is installed or started by this app.")
        st.sidebar.text("Endpoint: " + str(config["ollama_endpoint"]))
        st.sidebar.text("Model: " + (config["ollama_model"] or "not configured"))
        try:
            provider = OllamaProvider(config["ollama_endpoint"], config["ollama_model"], config["timeout_seconds"])
        except ProviderError as exc:
            st.error(str(exc) + " Explicitly select Offline demo to continue.")
            return
    service = HistoryService(db, provider)
    st.sidebar.caption(provider.name + " / " + provider.model)
    patient = db.patient(pid)
    st.sidebar.text("Selected: " + patient["label"])
    st.sidebar.caption(f"Last completed check-in: {patient['last_checkin'] or 'none'} · Next due: {patient['next_due']} (UTC)")
    if service.is_due(pid):
        st.warning("A demonstration check-in is due for the selected patient.")
    st.sidebar.caption("In-app notices only. No notification is delivered while the application is closed.")
    days = int(st.sidebar.number_input("Demonstration interval (days)", min_value=1, max_value=365, value=patient["interval_days"], key="interval_days"))
    if st.sidebar.button("Save interval", key="save_interval"):
        service.schedule(pid, "interval", days)
        st.rerun()
    if st.sidebar.button("Simulate check-in due", key="simulate_due"):
        service.schedule(pid, "simulate")
        st.rerun()
    if st.sidebar.button("Postpone check-in", key="postpone"):
        service.schedule(pid, "postpone", days)
        st.rerun()
    if st.session_state.get("flash"):
        st.success(st.session_state.pop("flash"))
    if role == "Patient interview":
        patient_screen(service, pid)
    elif role == "Simulated clinician":
        clinician_screen(service, pid)
    else:
        history_screen(service, pid)
    st.divider()
    st.caption("Patient-reported, not clinically verified. No production authentication, encryption-at-rest guarantee, audited tamper resistance, HIPAA-compliance, or clinical validation. Synthetic data only.")


try:
    main()
except (ValueError, ProviderError):
    # Input errors never echo source text or provider payloads into a traceback.
    st.error("Action could not be completed. Check required fields, selected patient, question neutrality, and session state. Already saved statements remain intact.")
