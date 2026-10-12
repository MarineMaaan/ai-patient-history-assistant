"""Reject unsafe citations and interpretation; render quotations from SQLite."""
from .models import Draft
from .retrieval import Search, supports_claim


class EvidenceError(ValueError):
    pass


def validate_draft(draft: Draft, patient_id: str, question: str, search: Search) -> Draft:
    by_id = {r["id"]: r for r in search.evidence}
    cited = set()
    for claim in draft.claims:
        for source_id in claim.source_ids:
            source = by_id.get(source_id)
            if source is None or source["patient_id"] != patient_id:
                raise EvidenceError("Citation is nonexistent, out of context, or belongs to another patient.")
            if not supports_claim(question, source):
                raise EvidenceError("Citation does not address the question.")
            if source["answer_state"] not in ("answered", "uncertain"):
                raise EvidenceError("A non-answer cannot support a patient-history claim.")
            if claim.text != source["answer"]:
                raise EvidenceError("Only full verbatim original answers are accepted in this version.")
            cited.add(source_id)
    required = {r["id"] for r in search.evidence if r["answer_state"] in ("answered", "uncertain") and supports_claim(question, r)}
    if cited != required:
        raise EvidenceError("Draft omitted relevant original statements, including potential contradictions.")
    if draft.outcome == "supported" and not draft.claims:
        raise EvidenceError("A supported answer requires evidence.")
    # App-assigned uncertainty survives even if the model attempts to omit it.
    flags = set(draft.uncertainty) | {"patient_report_only"}
    flags |= {r["answer_state"] for r in search.evidence if r["answer_state"] != "answered"}
    flags |= {r["relation"] for r in search.evidence if r["relation"]}
    if search.info["limited"]:
        flags.add("limited_search")
    draft.uncertainty = sorted(flags)
    if flags & {"unknown", "declined", "skipped", "uncertain", "conflict"}:
        draft.outcome = "uncertain" if draft.claims else "missing"
    elif draft.claims:
        draft.outcome = "supported"
    else:
        draft.outcome = "missing"
    return draft
