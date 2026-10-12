"""Editable library and conservative neutral-question gate."""
import json
from pathlib import Path
import re

from pydantic import TypeAdapter
from .models import LibraryQuestion

LIBRARY_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "questions.json"
LIBRARY = TypeAdapter(list[LibraryQuestion]).validate_python(json.loads(LIBRARY_PATH.read_text(encoding="utf-8")))
CONSCIOUSNESS_QUESTION = "What, if anything, do you remember about ever fainting, passing out, or losing consciousness?"


def unsafe_request(text: str) -> bool:
    # A demo guard, not a clinically validated safety classifier. Unknown phrasings
    # still cannot cause free-form claims or automatic patient-question conversion.
    return bool(re.search(
        r"diagnos|recommend|prescrib|dosage|what (?:should|must)|should (?:i|they|the patient)|"
        r"treat(?:ment)?|triage|emergency|consent|current wishes|on (?:his|her|their) behalf|"
        r"ignore.*instruction|system prompt|reveal.*patient|switch.*patient|"
        r"definitely|surely|you have|why (?:do|did).*have|confirm.*(?:disease|condition)", text, re.I))


def neutral_question(text: str) -> bool:
    return bool(text.strip()) and len(text) <= 1000 and text.count("?") == 1 and not unsafe_request(text)


def proposed_question(topic: str, detail: str | None = None) -> str:
    if detail == "dose":
        return "What dose, if any, do you remember taking for the medication you reported?"
    if detail == "frequency":
        return "How often, if at all, do you remember taking the medication you reported?"
    if detail == "exact_date":
        return "What date or approximate period do you remember for the event you reported, if any?"
    if topic == "consciousness":
        return CONSCIOUSNESS_QUESTION
    return next((q.question for q in LIBRARY if q.topic == topic),
                "What additional history, if any, would you like to report in your own words?")


def addresses_gap(topic: str, answer: str, state: str) -> bool:
    """Only narrow synthetic examples auto-resolve; other replies need review."""
    if state != "answered" or re.search(r"don't know|do not know|not sure|maybe|prefer not", answer, re.I):
        return False
    if topic == "consciousness":
        return bool(re.search(r"passed out|faint(?:ed|ing)?|lost consciousness|losing consciousness|never.*(?:passed|faint)|^(?:no|yes)[.!\s]*$", answer, re.I))
    return False
