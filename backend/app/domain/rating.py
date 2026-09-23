"""Рейтинг готовности задачи: 18 детерминированных проверок, 100 баллов.

Правила и баллы описаны в docs/rating-and-gamification.md. Меняются только вместе с документом и тестами.
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.domain.fields import CRITERIA, CriterionKey, FieldKey, LevelKey, level_for, next_level

MIN_FILLED_CHARS = 3
CONTEXT_DETAILED_MIN = 80
NEED_DETAILED_MIN = 60
USERS_SPECIFIC_MIN = 20

DATA_CONCRETE_RE = re.compile(
    r"\d|\b(?:csv|xlsx?|excel|json|sql|api|crm|erp|1с|1c|бд|баз[аеыу]|датасет\w*|таблиц\w*|выгрузк\w*|"
    r"журнал\w*|фото\w*|видео\w*|документ\w*|отчет\w*|записей|строк\w*|логи|логов|google sheets)\b"
)
DATA_ACCESS_RE = re.compile(
    r"\b(?:доступ\w*|nda|предостав\w*|переда\w*|пример\w*|образ[ец]\w*|демо\w*|обезлич\w*|анонимиз\w*|"
    r"тестов\w*|дадим)\b"
)
EXPECTED_ARTIFACT_RE = re.compile(
    r"\b(?:прототип\w*|mvp|бот\w*|дашборд\w*|dashboard|модел\w*|сервис\w*|приложени\w*|api|отчет\w*|"
    r"сайт\w*|скрипт\w*|интеграц\w*|панел\w*|алгоритм\w*|систем\w*)\b"
)
SUCCESS_MEASURABLE_RE = re.compile(r"\d|%|\b(?:не менее|не более|минимум|максимум)\b")
CONSTRAINTS_SPECIFIC_RE = re.compile(
    r"\d+\s*(?:дн\w*|день|недел\w*|месяц\w*|мес\b|час\w*|квартал\w*)"
    r"|\b\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?\b"
    r"|\b(?:python|java|javascript|typescript|react|1с|1c|sql|postgres\w*|docker|облак\w*|cloud|сервер\w*|"
    r"telegram|телеграм\w*|whatsapp|android|ios|api|доступ\w*|nda|vpn|бюджет\w*|персональн\w*)\b"
)
CONTACT_RE = re.compile(
    r"[\w.+-]+@[\w-]+\.[\w.-]+"
    r"|\+?\d[\d\s()\-]{8,}\d"
    r"|(?<![\w.])@[a-z0-9_]{4,}"
    r"|https?://\S+"
)
CADENCE_RE = re.compile(
    r"\b(?:раз в|еженедел\w*|ежедн\w*|ежемесяч\w*|кажд\w*|созвон\w*|встреч\w*|звон\w*|чат\w*|telegram|"
    r"телеграм\w*|zoom|meet|teams|почт\w*|email|e-mail|очно|онлайн|демо\w*)\b"
)

HINT_CONTEXT = (
    "Опишите, что происходит сейчас: как устроен процесс, где теряются время или деньги, "
    "насколько это массово"
)
HINT_NEED = (
    "Сформулируйте, что должно измениться после работы команды: какой процесс ускорить, упростить "
    "или автоматизировать"
)
HINT_DATA_FILLED = (
    "Укажите, какие данные или материалы есть. Даже «данных нет, нужно собрать» — полезная информация"
)
HINT_DATA_CONCRETE = (
    "Уточните источник, формат и объём. Например: «выгрузка из CRM, Excel, около 10 000 строк»"
)
HINT_DATA_ACCESS = (
    "Напишите, как команда получит данные: после NDA, обезличенная выгрузка, тестовый стенд, примеры"
)
HINT_EXPECTED = "Назовите результат: прототип, бот, дашборд, модель, исследование с рекомендациями"
HINT_SUCCESS = (
    "Добавьте измеримый критерий. Например: «не менее 40% обращений без оператора» "
    "или «отчёт за 5 минут вместо 2 часов»"
)
HINT_CONSTRAINTS = "Укажите сроки, обязательные технологии, ограничения доступа или бюджет"
HINT_USERS = "Опишите, кто будет пользоваться решением: роли, отделы, сегменты клиентов"
HINT_CONTACT = "Оставьте контакт: имя и роль, email, телефон или @telegram"
HINT_INTERACTION = (
    "Опишите, как часто и где вы готовы консультировать команду. "
    "Например: «созвон раз в неделю, вопросы в Telegram-чате»"
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("ё", "е").replace("Ё", "Е").lower()).strip()


def _has_text(text: str) -> bool:
    return len(re.sub(r"\s+", "", text)) >= MIN_FILLED_CHARS


def _min_length(limit: int) -> Callable[[str], bool]:
    return lambda text: len(text.strip()) >= limit


def _pattern(regex: re.Pattern[str]) -> Callable[[str], bool]:
    return lambda text: regex.search(normalize(text)) is not None


@dataclass(frozen=True)
class CheckDef:
    id: str
    criterion: CriterionKey
    field: FieldKey
    points: int
    label: str
    hint: str
    rule: Callable[[str], bool]


CHECKS: tuple[CheckDef, ...] = (
    CheckDef("context.filled", "context_need", "context", 6, "Контекст описан", HINT_CONTEXT, _has_text),
    CheckDef(
        "context.detailed",
        "context_need",
        "context",
        4,
        "Контекст подробный",
        HINT_CONTEXT,
        _min_length(CONTEXT_DETAILED_MIN),
    ),
    CheckDef("need.filled", "context_need", "need", 6, "Потребность описана", HINT_NEED, _has_text),
    CheckDef(
        "need.detailed",
        "context_need",
        "need",
        4,
        "Потребность конкретная",
        HINT_NEED,
        _min_length(NEED_DETAILED_MIN),
    ),
    CheckDef("data.filled", "data", "data", 10, "Указаны данные или материалы", HINT_DATA_FILLED, _has_text),
    CheckDef(
        "data.concrete",
        "data",
        "data",
        6,
        "Есть источник, формат или объём",
        HINT_DATA_CONCRETE,
        _pattern(DATA_CONCRETE_RE),
    ),
    CheckDef(
        "data.access",
        "data",
        "data",
        4,
        "Понятно, как команда получит данные",
        HINT_DATA_ACCESS,
        _pattern(DATA_ACCESS_RE),
    ),
    CheckDef(
        "expected_result.filled",
        "expected_result",
        "expected_result",
        8,
        "Результат описан",
        HINT_EXPECTED,
        _has_text,
    ),
    CheckDef(
        "expected_result.artifact",
        "expected_result",
        "expected_result",
        7,
        "Назван конкретный артефакт",
        HINT_EXPECTED,
        _pattern(EXPECTED_ARTIFACT_RE),
    ),
    CheckDef(
        "success_criteria.filled",
        "success_criteria",
        "success_criteria",
        7,
        "Критерии успеха указаны",
        HINT_SUCCESS,
        _has_text,
    ),
    CheckDef(
        "success_criteria.measurable",
        "success_criteria",
        "success_criteria",
        8,
        "Критерии измеримы",
        HINT_SUCCESS,
        _pattern(SUCCESS_MEASURABLE_RE),
    ),
    CheckDef(
        "constraints.filled",
        "constraints",
        "constraints",
        5,
        "Ограничения указаны",
        HINT_CONSTRAINTS,
        _has_text,
    ),
    CheckDef(
        "constraints.specific",
        "constraints",
        "constraints",
        5,
        "Есть срок, технология или доступ",
        HINT_CONSTRAINTS,
        _pattern(CONSTRAINTS_SPECIFIC_RE),
    ),
    CheckDef("users.filled", "users", "users", 6, "Пользователи указаны", HINT_USERS, _has_text),
    CheckDef(
        "users.specific",
        "users",
        "users",
        4,
        "Описаны конкретные роли или сегмент",
        HINT_USERS,
        _min_length(USERS_SPECIFIC_MIN),
    ),
    CheckDef(
        "contact.valid",
        "business_link",
        "contact",
        5,
        "Есть рабочий контакт",
        HINT_CONTACT,
        _pattern(CONTACT_RE),
    ),
    CheckDef(
        "interaction_format.filled",
        "business_link",
        "interaction_format",
        3,
        "Формат взаимодействия указан",
        HINT_INTERACTION,
        _has_text,
    ),
    CheckDef(
        "interaction_format.cadence",
        "business_link",
        "interaction_format",
        2,
        "Понятны частота или канал связи",
        HINT_INTERACTION,
        _pattern(CADENCE_RE),
    ),
)

ACHIEVEMENTS: tuple[tuple[str, str, str], ...] = (
    ("context_need", "Понятная боль", "Контекст и потребность раскрыты полностью"),
    ("data", "Данные на столе", "Понятно, какие данные есть и как их получить"),
    ("expected_result", "Ясная цель", "Назван конкретный результат работы команды"),
    ("success_criteria", "Измеримо", "Критерии успеха можно проверить цифрами"),
    ("constraints", "Рамки заданы", "Указаны сроки, технологии или доступы"),
    ("users", "Знаем пользователя", "Понятно, для кого решение"),
    ("business_link", "На связи", "Есть контакт и формат обратной связи"),
)
PERFECT_ACHIEVEMENT = ("perfect", "Идеальная карточка", "Рейтинг 100 из 100")


class Check(BaseModel):
    id: str
    label: str
    field: FieldKey
    points: int
    passed: bool


class CriterionScore(BaseModel):
    criterion: CriterionKey
    label: str
    max: int
    earned: int
    checks: list[Check]


class MissingItem(BaseModel):
    check_id: str
    criterion: CriterionKey
    field: FieldKey
    hint: str
    points_gain: int


class Level(BaseModel):
    key: LevelKey
    label: str
    min: int
    max: int


class NextLevel(BaseModel):
    key: LevelKey
    label: str
    points_needed: int


class Achievement(BaseModel):
    key: str
    label: str
    description: str
    earned: bool


class Rating(BaseModel):
    score: int
    potential_score: int
    delta: int
    level: Level
    next_level: NextLevel | None
    breakdown: list[CriterionScore]
    missing: list[MissingItem]
    achievements: list[Achievement]


def counted_value(card: Mapping[str, Any], field: str, *, include_suggested: bool = False) -> str | None:
    """Значение поля, если оно даёт баллы: подтверждено (или предложено — для потенциала)."""
    entry = card.get(field) or {}
    value = entry.get("value")
    allowed = ("confirmed", "suggested") if include_suggested else ("confirmed",)
    if entry.get("status") in allowed and isinstance(value, str) and value.strip():
        return value
    return None


def _evaluate(card: Mapping[str, Any], *, include_suggested: bool) -> list[tuple[CheckDef, bool]]:
    results = []
    for check in CHECKS:
        value = counted_value(card, check.field, include_suggested=include_suggested)
        results.append((check, value is not None and _has_text(value) and check.rule(value)))
    return results


def score_card(card: Mapping[str, Any], *, include_suggested: bool = False) -> int:
    return sum(
        check.points for check, passed in _evaluate(card, include_suggested=include_suggested) if passed
    )


def field_gain(card: Mapping[str, Any], field: str) -> int:
    """Сколько баллов ещё можно получить за поле: сумма невыполненных проверок."""
    return sum(
        check.points
        for check, passed in _evaluate(card, include_suggested=False)
        if check.field == field and not passed
    )


def compute_rating(card: Mapping[str, Any], *, previous_score: int | None = None) -> Rating:
    results = _evaluate(card, include_suggested=False)
    score = sum(check.points for check, passed in results if passed)

    breakdown = []
    for criterion in CRITERIA:
        checks = [
            Check(id=check.id, label=check.label, field=check.field, points=check.points, passed=passed)
            for check, passed in results
            if check.criterion == criterion.key
        ]
        breakdown.append(
            CriterionScore(
                criterion=criterion.key,
                label=criterion.label,
                max=criterion.weight,
                earned=sum(item.points for item in checks if item.passed),
                checks=checks,
            )
        )

    missing = sorted(
        (
            MissingItem(
                check_id=check.id,
                criterion=check.criterion,
                field=check.field,
                hint=check.hint,
                points_gain=check.points,
            )
            for check, passed in results
            if not passed
        ),
        key=lambda item: -item.points_gain,
    )

    earned_by_criterion = {item.criterion: item.earned == item.max for item in breakdown}
    achievements = [
        Achievement(key=key, label=label, description=description, earned=earned_by_criterion[key])
        for key, label, description in ACHIEVEMENTS
    ]
    perfect_key, perfect_label, perfect_description = PERFECT_ACHIEVEMENT
    achievements.append(
        Achievement(
            key=perfect_key, label=perfect_label, description=perfect_description, earned=score == 100
        )
    )

    level = level_for(score)
    upcoming = next_level(score)
    return Rating(
        score=score,
        potential_score=score_card(card, include_suggested=True),
        delta=score - previous_score if previous_score is not None else 0,
        level=Level(key=level.key, label=level.label, min=level.min, max=level.max),
        next_level=(
            NextLevel(key=upcoming.key, label=upcoming.label, points_needed=upcoming.min - score)
            if upcoming
            else None
        ),
        breakdown=breakdown,
        missing=missing,
        achievements=achievements,
    )
