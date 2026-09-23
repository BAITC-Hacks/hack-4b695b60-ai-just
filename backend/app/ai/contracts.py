"""Граница между ядром backend (A1) и AI-слоем (A2). Сигнатуры меняются только по договорённости."""

from typing import Protocol

from pydantic import BaseModel

from app.domain.fields import FieldKey


class EvidenceOut(BaseModel):
    source: str
    """«draft» или «answer:<question_id>»."""
    quote: str
    """Дословная цитата из источника."""


class FieldSuggestion(BaseModel):
    field: FieldKey
    value: str
    evidence: list[EvidenceOut]


class QuestionOut(BaseModel):
    field: FieldKey
    question: str
    why: str


class DraftAnalysis(BaseModel):
    fields: list[FieldSuggestion]
    missing: list[FieldKey]
    questions: list[QuestionOut]
    topic: str | None


class CardBuild(BaseModel):
    fields: list[FieldSuggestion]
    unresolved: list[FieldKey]


class QAPair(BaseModel):
    question_id: str
    field: FieldKey
    question: str
    answer: str


class AICallMeta(BaseModel):
    provider: str
    model: str
    degraded: bool
    trace_ids: list[int]


class AIService(Protocol):
    def analyze_draft(
        self, draft: str, topic: str | None, task_id: int | None
    ) -> tuple[DraftAnalysis, AICallMeta]: ...

    def build_card(
        self, draft: str, qa: list[QAPair], confirmed: dict[str, str], task_id: int | None
    ) -> tuple[CardBuild, AICallMeta]: ...
