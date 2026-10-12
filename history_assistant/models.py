"""Validated input/output contracts. Structure alone never proves truth."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AnswerState = Literal["answered", "unknown", "declined", "skipped", "uncertain"]
Relation = Literal["correction", "change", "conflict", "clarification"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Submission(StrictModel):
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(max_length=4000)
    state: AnswerState = "answered"
    topic: str = Field(min_length=1, max_length=100)
    origin: Literal["library", "followup", "clarification", "correction", "seed"]
    respondent: str = Field(min_length=1, max_length=100)
    event_wording: str = Field(default="", max_length=300)
    event_precision: Literal["unknown", "approximate", "year", "month", "day"] = "unknown"
    related_to: str | None = None
    relation: Relation | None = None
    followup_id: str | None = None

    @model_validator(mode="after")
    def coherent(self):
        if self.state in ("answered", "uncertain") and not self.answer.strip():
            raise ValueError("An answer is required; use Skip for no response.")
        if bool(self.related_to) != bool(self.relation):
            raise ValueError("A linked statement and relationship must be supplied together.")
        if self.event_precision != "unknown" and not self.event_wording.strip():
            raise ValueError("Date precision requires original patient date wording.")
        return self


class Claim(StrictModel):
    # v1 deliberately accepts only full verbatim answers. The app renders DB text.
    text: str = Field(min_length=1, max_length=4000)
    source_ids: list[str] = Field(min_length=1, max_length=10)


class Draft(StrictModel):
    claims: list[Claim] = Field(default_factory=list, max_length=50)
    uncertainty: list[Literal[
        "patient_report_only", "unknown", "declined", "skipped", "uncertain",
        "correction", "change", "conflict", "clarification", "limited_search", "detail_not_recorded"
    ]] = Field(default_factory=lambda: ["patient_report_only"], max_length=20)
    outcome: Literal["supported", "missing", "uncertain"]


class Clarification(StrictModel):
    question: str | None = Field(default=None, max_length=1000)


class LibraryQuestion(StrictModel):
    id: str
    topic: str
    question: str = Field(min_length=1, max_length=1000)
