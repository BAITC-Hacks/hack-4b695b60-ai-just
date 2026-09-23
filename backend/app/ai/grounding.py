"""Conservative extraction checks, not a semantic truth or entailment model.

Values must reproduce complete cited fragments, including roles and contacts. This
deliberately rejects free paraphrases and leaves uncertain fields for human input.
It cannot establish that the user's source is true or that its field label is right.
"""

import re
from collections.abc import Mapping

from app.ai.contracts import EvidenceOut, FieldSuggestion
from app.ai.pii import EMAIL_RE, HANDLE_RE

URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
NUMBER_RE = re.compile(r"(?<!\w)\d+(?:[\s\u00a0]\d{3})*(?:[.,]\d+)?(?!\w)")
STRIP_RE = re.compile(r"[«»\"'“”‘’]")
SPACE_RE = re.compile(r"\s+")
SENTENCE_RE = re.compile(r"(?<=[.!?;])\s+|\n+")
CLAUSE_RE = re.compile(r";\s*|,\s*(?=(?:чтобы|потому что|так как|а то|поэтому)\b)", re.IGNORECASE)
USER_ROLE_RE = re.compile(
    r"\b(?:клиент|покупател|пользовател|сотрудник|оператор|менеджер|администратор|"
    r"студент|школьник|ученик|учител|преподавател|куратор|врач|пациент|агроном|"
    r"фермер|водител|курьер|закупщик)\w*",
    re.IGNORECASE,
)
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
    # Fuzzy matching can turn "нет доступа" into "есть доступ" or accept a changed
    # digit. Citation text must occur exactly, allowing only display normalization.
    return bool(quote) and re.search(r"(?<!\w)" + re.escape(quote) + r"(?!\w)", source_text) is not None


def _canonical_value(text: str) -> str:
    """Normalize display-only number spacing while retaining signs and qualifiers."""
    return NUMBER_RE.sub(
        lambda match: match.group(0).replace(" ", "").replace("\u00a0", "").replace(",", "."),
        normalized(text),
    )


def _complete_fragment(evidence: EvidenceOut, sources: Mapping[str, str]) -> bool:
    source = factual_text(sources[evidence.source])
    quote = normalized(evidence.quote)
    sentences = [part.strip() for part in SENTENCE_RE.split(source) if part.strip()]
    fragments = [source, *sentences, *(part for sentence in sentences for part in CLAUSE_RE.split(sentence))]
    return quote in {normalized(part) for part in fragments if "?" not in part}


def _value_supported(suggestion: FieldSuggestion, sources: Mapping[str, str]) -> bool:
    if not all(_complete_fragment(item, sources) for item in suggestion.evidence):
        return False
    # Only whole quoted fragments may be joined, so dropping a negation or
    # borrowing a number from another field cannot silently change a statement.
    quotes = [item.quote.strip().rstrip(".,;:!?") for item in suggestion.evidence]
    value = _canonical_value(suggestion.value)
    return any(value == _canonical_value(separator.join(quotes)) for separator in (". ", ", ", "; ", "\n"))


def check_suggestion(suggestion: FieldSuggestion, sources: Mapping[str, str]) -> str | None:
    if not suggestion.value.strip():
        return "empty_value"
    if len(suggestion.value) > (80 if suggestion.field == "title" else 2000):
        return "value_too_long"
    if not suggestion.evidence or not all(evidence_found(item, sources) for item in suggestion.evidence):
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
    if not _value_supported(suggestion, sources):
        return "value_not_supported_by_quotes"
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
