import json
import sqlite3

import httpx
import pytest

from history_assistant.evidence import EvidenceError, validate_draft
from history_assistant.models import Claim, Clarification, Draft, Submission
from history_assistant.providers import OllamaProvider, ProviderError
from history_assistant.retrieval import retrieve


def test_offtopic_response_does_not_support_consciousness_claim(service):
    pid = "patient-a"
    sid = service.start_session(pid, "interview", "irrelevant")
    row = service.submit(pid, sid, Submission(question="Have you ever lost consciousness?", answer="My favorite color is green.", topic="consciousness", origin="library", respondent="synthetic"), "irrelevant")
    search = retrieve(service.db.records("exchanges", pid), "Has the patient lost consciousness?")
    with pytest.raises(EvidenceError):
        validate_draft(Draft(outcome="supported", claims=[Claim(text=row["answer"], source_ids=[row["id"]])]), pid, "Has the patient lost consciousness?", search)
    output = service.query(pid, "Has the patient lost consciousness?", "Synthetic", "irrelevant-query")
    assert not json.loads(output["payload"])["claims"]


@pytest.mark.parametrize("question", ["What treatment should you use?", "What color is your car?", "What medical conditions, if any, have you previously been told you have?"])
def test_bad_clarification_is_visible_and_never_saved(service, question):
    class MockClarifier:
        name, model = "Mock", "not-live"
        def clarify(self, *args):
            return Clarification(question=question)
    service.provider = MockClarifier()
    rows = service.db.records("exchanges", "patient-a")
    draft, error = service.clarification("patient-a", rows[0]["id"])
    assert draft is None and error
    assert service.db.records("exchanges", "patient-a") == rows


def test_sqlite_cross_patient_source_relation_rejected(service):
    output = service.summary("patient-a")
    other = service.db.records("exchanges", "patient-b")[0]
    with pytest.raises(sqlite3.IntegrityError):
        with service.db.connect() as conn:
            conn.execute("INSERT INTO output_sources VALUES(?,?,?)", (output["id"], other["id"], "patient-a"))
    with service.db.connect() as conn:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_stale_summary_review_refused_but_snapshot_preserved(service):
    output = service.summary("patient-a")
    sid = service.start_session("patient-a", "interview", "revision")
    service.submit("patient-a", sid, Submission(question="Any changes?", answer="I have nothing to add.", topic="changes", origin="library", respondent="synthetic"), "revision")
    with pytest.raises(ValueError):
        service.approve_summary("patient-a", output["id"])
    assert service.db.get("outputs", output["id"], "patient-a") == output
    fresh = service.summary("patient-a")
    service.approve_summary("patient-a", fresh["id"])
    service.approve_summary("patient-a", fresh["id"])
    assert len([e for e in service.db.records("activity", "patient-a") if e["action"] == "patient_summary_review"]) == 1


def test_nonobject_json_provider_failure_is_bounded():
    calls = []
    def response(request):
        calls.append(request.url.path)
        return httpx.Response(200, json=["invalid envelope"])
    provider = OllamaProvider("http://127.0.0.1:11434", "mock-local", transport=httpx.MockTransport(response))
    with pytest.raises(ProviderError):
        provider.confirm_local()
    assert len(calls) == 2


def test_topic_mention_is_not_evidence_of_requested_dosage(service):
    output = service.query("patient-a", "What dose of medication was reported?", "Synthetic", "dose-query")
    assert "detail_not_recorded" in json.loads(output["payload"])["uncertainty"]
    assert json.loads(output["payload"])["outcome"] == "uncertain"
    gap = service.db.records("followups", "patient-a")[0]
    assert gap["gap_key"] == "medications:dose" and "What dose" in gap["question"]
