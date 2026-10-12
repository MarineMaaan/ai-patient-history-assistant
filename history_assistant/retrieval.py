"""Transparent topic/text search over original exchanges only; never AI outputs."""
from dataclasses import dataclass
import re

TOPICS = {
    "consciousness": ("consciousness", "passed out", "pass out", "faint", "blackout", "blacked out"),
    "medications": ("medication", "medicine", "medicines", "drug", "inhaler", "tablet", "pill"),
    "allergies": ("allerg", "reaction"),
    "procedures": ("procedure", "surgery", "surgeries", "operation", "appendectomy"),
    "family": ("family", "relative", "parent", "mother", "father"),
    "conditions": ("condition", "medical history", "asthma", "migraine", "diabetes"),
    "changes": ("changed", "changes", "since", "check-in"),
}
STOP_WORDS = set("has have had ever the a an about patient fictional reported record records history what whether is did does do you i it their they of in to any previously tell me please".split())


def topic_for(text: str) -> str | None:
    lowered = text.lower()
    return next((topic for topic, terms in TOPICS.items() if any(t in lowered for t in terms)), None)


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP_WORDS and len(w) > 2}


def relevant(question: str, exchange: dict) -> bool:
    topic = topic_for(question)
    if question == "Summarize the recorded history":
        return True
    if topic:
        if exchange["topic"] != topic:
            # A free response on a different topic can still explicitly address this topic.
            return any(t in exchange["answer"].lower() for t in TOPICS[topic])
        # Specific entities must occur in source text, not merely share a broad category.
        entity_terms = {"asthma", "migraine", "diabetes", "penicillin", "latex", "ibuprofen", "aspirin", "seizure"}
        specified = tokens(question) & entity_terms
        return not specified or bool(specified & tokens(exchange["question"] + " " + exchange["answer"]))
    return bool(tokens(question) & tokens(exchange["question"] + " " + exchange["answer"]))


def supports_claim(question: str, exchange: dict) -> bool:
    """Topic match alone isn't enough: an off-topic answer isn't evidence.

    For the defining consciousness example, accept explicit reports/denials or
    brief yes/no answers in their eliciting context. Other topics use conservative
    text/entity retrieval and verbatim-only display, not clinical entailment.
    """
    if not relevant(question, exchange):
        return False
    if topic_for(question) == "consciousness":
        return bool(re.search(r"consciousness|pass(?:ed|ing)? out|faint|black(?:ed)? out|blackout|^(?:no|yes)[.!\s]*$", exchange["answer"], re.I))
    return True


def missing_detail(question: str, evidence: list[dict]) -> str | None:
    """Small demo facets distinguish a topic mention from a requested detail."""
    text = question.lower()
    answers = " ".join(r["answer"] for r in evidence if r["answer_state"] == "answered")
    if re.search(r"dose|dosage|how much", text) and not re.search(r"\d+\s*(?:mg|mcg|ml|puffs?|tablets?)\b", answers, re.I):
        return "dose"
    if re.search(r"how often|frequency", text) and not re.search(r"daily|weekly|monthly|times? (?:a|per)|as needed", answers, re.I):
        return "frequency"
    if re.search(r"exact (?:day|date)", text) and not any(r["event_precision"] == "day" and r["event_wording"] for r in evidence):
        return "exact_date"
    return None


@dataclass
class Search:
    evidence: list[dict]
    info: dict


def retrieve(records: list[dict], question: str, max_records: int = 50, max_chars: int = 40000) -> Search:
    matches = [r for r in records if relevant(question, r)]
    # Pull the whole linked correction chain, including earlier statements and children.
    ids = {r["id"] for r in matches}
    while True:
        linked = {r["id"] for r in records if r["related_to"] in ids or r["id"] in {
            x["related_to"] for x in records if x["id"] in ids}}
        if linked <= ids:
            break
        ids |= linked
    matches = [r for r in records if r["id"] in ids]
    char_count = sum(len(r["question"]) + len(r["answer"]) + 500 for r in matches)
    limited = len(matches) > max_records or char_count > max_chars
    # Fail closed on context overflow; don't silently drop a contradiction.
    return Search(matches, {
        "searched_count": len(records), "relevant_count": len(matches),
        "date_start": min((r["recorded_at"] for r in records), default=None),
        "date_end": max((r["recorded_at"] for r in records), default=None),
        "limited": limited, "max_records": max_records, "max_chars": max_chars,
        "method": "topic/text over all selected-patient original exchanges; linked records included",
    })
