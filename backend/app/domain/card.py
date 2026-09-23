"""Операции с карточкой задачи. Инвариант: AI никогда не перезаписывает подтверждённые поля."""

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from app.domain.fields import FIELD_KEYS

Card = dict[str, dict[str, Any]]


def iso(moment: datetime) -> str:
    utc = moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)
    return utc.replace(microsecond=0, tzinfo=None).isoformat() + "Z"


def empty_field() -> dict[str, Any]:
    return {"value": None, "status": "empty", "source": None, "evidence": [], "updated_at": None}


def empty_card() -> Card:
    return {key: empty_field() for key in FIELD_KEYS}


def normalize_card(card: Mapping[str, Any] | None) -> Card:
    """Глубокая копия карточки, в которой гарантированно есть все 10 полей."""
    result = empty_card()
    for key in FIELD_KEYS:
        if card and isinstance(card.get(key), Mapping):
            entry = dict(card[key])
            result[key] = {
                **empty_field(),
                **entry,
                "evidence": [dict(item) for item in entry.get("evidence") or []],
            }
    return result


def user_field(value: str | None, now: datetime) -> dict[str, Any]:
    text = (value or "").strip()
    if not text:
        return {**empty_field(), "updated_at": iso(now)}
    return {"value": text, "status": "confirmed", "source": "user", "evidence": [], "updated_at": iso(now)}


def ai_field(value: str, evidence: list[dict[str, str]], now: datetime) -> dict[str, Any]:
    return {
        "value": value,
        "status": "suggested",
        "source": "ai",
        "evidence": evidence,
        "updated_at": iso(now),
    }


def apply_suggestions(
    card: Mapping[str, Any], suggestions: Iterable[tuple[str, str, list[dict[str, str]]]], now: datetime
) -> tuple[Card, list[str]]:
    """Предложения AI попадают только в пустые и неподтверждённые поля."""
    result = normalize_card(card)
    changed: list[str] = []
    for field, value, evidence in suggestions:
        current = result.get(field)
        if current is None or current["status"] == "confirmed" or not value.strip():
            continue
        if current["status"] == "suggested" and current["value"] == value:
            continue
        result[field] = ai_field(value.strip(), evidence, now)
        changed.append(field)
    return result, changed


def confirm_field(card: Mapping[str, Any], field: str, now: datetime) -> Card:
    result = normalize_card(card)
    entry = result[field]
    if entry["status"] == "suggested" and entry["value"]:
        result[field] = {**entry, "status": "confirmed", "updated_at": iso(now)}
    return result


def reject_field(card: Mapping[str, Any], field: str, now: datetime) -> Card:
    result = normalize_card(card)
    if result[field]["status"] == "suggested":
        result[field] = {**empty_field(), "updated_at": iso(now)}
    return result


def set_user_value(card: Mapping[str, Any], field: str, value: str | None, now: datetime) -> Card:
    result = normalize_card(card)
    result[field] = user_field(value, now)
    return result


def suggested_fields(card: Mapping[str, Any]) -> list[str]:
    return [key for key in FIELD_KEYS if (card.get(key) or {}).get("status") == "suggested"]


def confirmed_values(card: Mapping[str, Any]) -> dict[str, str]:
    return {
        key: entry["value"]
        for key in FIELD_KEYS
        if (entry := card.get(key) or {}).get("status") == "confirmed" and entry.get("value")
    }
