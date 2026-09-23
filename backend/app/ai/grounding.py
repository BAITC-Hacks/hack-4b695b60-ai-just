"""Deterministic evidence, number and contact checks for model suggestions."""

import re
from collections.abc import Mapping

from rapidfuzz.fuzz import partial_ratio

from app.ai.contracts import EvidenceOut, FieldSuggestion
from app.ai.pii import EMAIL_RE, HANDLE_RE

URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
NUMBER_RE = re.compile(r"(?<!\w)\d+(?:[\s\u00a0]\d{3})*(?:[.,]\d+)?(?!\w)")
STRIP_RE = re.compile(r"[«»\"'“”‘’]")
SPACE_RE = re.compile(r"\s+")
SENTENCE_RE = re.compile(r"(?<=[.!?;])\s+|\n+")
INSTRUCTION_RE = re.compile(
    r"\b(?:игнорируй|забудь|укажи|впиши|выведи|ответь|"
    r"ignore\s+(?:all\s+)?(?:previous\s+)?instructions|"
    r"you\s+are\s+now|system\s*:|assistant\s*:)\b",
    re.IGNORECASE,
)


def factual_text(text: str) -> str:
    """Drop explicit commands addressed to the model from evidence sources."""
    return " ".join(part for part in SENTENCE_RE.split(text) if not INSTRUCTION_RE.search(part))


def normalized(text: str) -> str:
    return SPACE_RE.sub(" ", STRIP_RE.sub("", text.lower().replace("ё", "е"))).strip(" .,:;!?\t\r\n")


def numbers(text: str) -> set[str]:
    return {
        match.group(0).replace(" ", "").replace("\u00a0", "").replace(",", ".")
        for match in NUMBER_RE.finditer(text)
    }


def entities(text: str) -> set[str]:
    values = [
        match.group(0).rstrip(".,;!?)")
        for pattern in (EMAIL_RE, URL_RE, HANDLE_RE)
        for match in pattern.finditer(text)
    ]
    return {value.casefold() for value in values}


def evidence_found(evidence: EvidenceOut, sources: Mapping[str, str]) -> bool:
    source = sources.get(evidence.source)
    if not source or not evidence.quote.strip():
        return False
    quote, source_text = normalized(evidence.quote), normalized(factual_text(source))
    return bool(quote) and (quote in source_text or partial_ratio(quote, source_text) >= 90)


def check_suggestion(suggestion: FieldSuggestion, sources: Mapping[str, str]) -> str | None:
    if not suggestion.value.strip():
        return "empty_value"
    if len(suggestion.value) > (80 if suggestion.field == "title" else 2000):
        return "value_too_long"
    if not any(evidence_found(item, sources) for item in suggestion.evidence):
        return "evidence_not_found"
    all_sources = "\n".join(factual_text(source) for source in sources.values())
    source_numbers = numbers(all_sources)
    for number in sorted(numbers(suggestion.value)):
        if number not in source_numbers:
            return f"number_not_in_source:{number}"
    source_entities = entities(all_sources)
    for entity in sorted(entities(suggestion.value)):
        if entity not in source_entities:
            return f"entity_not_in_source:{entity}"
    return None


def filter_grounded(
    suggestions: list[FieldSuggestion], sources: Mapping[str, str], confirmed: Mapping[str, str] | None = None
) -> tuple[list[FieldSuggestion], list[dict[str, str]]]:
    accepted: list[FieldSuggestion] = []
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()
    for suggestion in suggestions:
        if suggestion.field in seen or suggestion.field in (confirmed or {}):
            continue
        seen.add(suggestion.field)
        reason = check_suggestion(suggestion, sources)
        if reason:
            rejected.append({"field": suggestion.field, "value": suggestion.value, "reason": reason})
        else:
            accepted.append(suggestion)
    return accepted, rejected
