"""Офлайн-заглушка AIService: правила по ключевым словам, без сети.

Значения полей — дословные фрагменты текста пользователя, поэтому заглушка grounded по построению.
"""

import re
from collections.abc import Iterable

from app.ai.contracts import (
    AICallMeta,
    CardBuild,
    DraftAnalysis,
    EvidenceOut,
    FieldSuggestion,
    QAPair,
)
from app.ai.question_bank import select_questions
from app.config import get_settings
from app.domain.fields import SCORED_FIELD_KEYS, TOPIC_KEYS, FieldKey
from app.domain.rating import CONTACT_RE, field_gain, normalize

STUB_PROVIDER = "stub"
STUB_MODEL = "rules-v1"
TITLE_MAX = 80

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_CLAUSE_SPLIT_RE = re.compile(r";\s*|,\s*(?=(?:чтобы|потому что|так как|а то|поэтому)\b)", re.IGNORECASE)

_CLAUSE_RULES: tuple[tuple[FieldKey, re.Pattern[str]], ...] = (
    (
        "data",
        re.compile(
            r"\b(?:данн\w*|выгрузк\w*|таблиц\w*|excel|csv|баз[аеыу]|crm|логи|журнал\w*|фото\w*|документ\w*|"
            r"архив\w*|датасет\w*|чек(?:и|ов)|записей)\b"
        ),
    ),
    (
        "success_criteria",
        re.compile(
            r"\b(?:не менее|не более|не ниже|не выше|kpi|метрик\w*|показател\w*|критери\w*|"
            r"успех\w*|точност\w*)\b"
        ),
    ),
    (
        "constraints",
        re.compile(
            r"\b(?:срок\w*|дедлайн\w*|недел[иью]|месяц\w*|бюджет\w*|технолог\w*|python|1с|1c|доступ\w*|nda|"
            r"огранич\w*|android|ios|без интернета)\b"
        ),
    ),
    (
        "expected_result",
        re.compile(
            r"\b(?:хотим|нужен|нужна|нужно|сделать|создать|разработать|бот\w*|прототип\w*|дашборд\w*|"
            r"приложени\w*|сервис\w*|модел\w*|систем\w*|автопроверк\w*)\b"
        ),
    ),
    (
        "need",
        re.compile(
            r"\b(?:чтобы|снизить|сократить|увеличить|ускорить|автоматизир\w*|улучшить|избавиться|меньше|больше|"
            r"раньше)\b"
        ),
    ),
    (
        "interaction_format",
        re.compile(
            r"\b(?:созвон\w*|встреч\w*|раз в|чат(?!-?бот)\w*|telegram(?!-?бот)|телеграм(?!-?бот)\w*|"
            r"zoom|онлайн|очно|консульт\w*)\b"
        ),
    ),
    (
        "context",
        re.compile(
            r"\b(?:сейчас|сегодня|вручную|приходится|проблем\w*|тратим|тратят|теряем|теряется|теряются|"
            r"жалуются|не видят|не успевают|получает|получаем)\b"
        ),
    ),
)

_SECONDARY_ANSWER_FIELDS: frozenset[str] = frozenset({"constraints", "interaction_format"})

_USER_LABELS: tuple[tuple[str, str], ...] = (
    ("клиент", "Клиенты"),
    ("покупател", "Покупатели"),
    ("пользовател", "Пользователи"),
    ("сотрудник", "Сотрудники"),
    ("оператор", "Операторы"),
    ("менеджер", "Менеджеры"),
    ("администратор", "Администраторы"),
    ("студент", "Студенты"),
    ("школьник", "Школьники"),
    ("ученик", "Ученики"),
    ("учител", "Учителя"),
    ("преподавател", "Преподаватели"),
    ("куратор", "Кураторы"),
    ("врач", "Врачи"),
    ("пациент", "Пациенты"),
    ("агроном", "Агрономы"),
    ("фермер", "Фермеры"),
    ("водител", "Водители"),
    ("курьер", "Курьеры"),
    ("закупщик", "Закупщики"),
)
_USER_WORD_RE = re.compile(r"\b(" + "|".join(stem for stem, _ in _USER_LABELS) + r")\w*", re.IGNORECASE)

_TOPIC_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("logistics", re.compile(r"\b(?:логист\w*|доставк\w*|склад\w*|курьер\w*|груз\w*|маршрут\w*)\b")),
    ("retail", re.compile(r"\b(?:магазин\w*|ритейл\w*|покупател\w*|касс[аеыу]|товар\w*)\b")),
    ("finance", re.compile(r"\b(?:банк\w*|кредит\w*|финанс\w*|платеж\w*|заем\w*|заемщик\w*)\b")),
    (
        "education",
        re.compile(
            r"\b(?:студент\w*|школ\w*|обучени\w*|курс\w*|учени\w*|"
            r"преподавател\w*|универс\w*)\b"
        ),
    ),
    ("healthcare", re.compile(r"\b(?:пациент\w*|клиник\w*|врач\w*|медиц\w*|больниц\w*)\b")),
    ("agro", re.compile(r"\b(?:агро\w*|ферм\w*|урожа\w*|посев\w*|пшениц\w*|скот\w*|пол(?:е|я|ей))\b")),
    ("government", re.compile(r"\b(?:госуд\w*|акимат\w*|граждан\w*|госуслуг\w*|министерств\w*)\b")),
    ("manufacturing", re.compile(r"\b(?:завод\w*|производств\w*|цех\w*|оборудовани\w*|станк\w*)\b")),
    ("it_telecom", re.compile(r"\b(?:телеком\w*|хостинг\w*|операторы? связи)\b")),
)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part and part.strip()]


def _clauses(text: str) -> list[str]:
    result = []
    for sentence in _sentences(text):
        result.extend(part.strip() for part in _CLAUSE_SPLIT_RE.split(sentence) if part and part.strip())
    return result


def _quote(fragment: str) -> str:
    return fragment.strip().rstrip(".,;:!?").strip()


def _compose(fragments: Iterable[str]) -> str:
    parts = []
    for fragment in fragments:
        text = _quote(fragment)
        if text:
            parts.append(text[0].upper() + text[1:])
    return ". ".join(parts) + "." if parts else ""


def _classify(clause: str) -> FieldKey | None:
    text = normalize(clause)
    best: FieldKey | None = None
    best_hits = 0
    for field, pattern in _CLAUSE_RULES:
        hits = len(pattern.findall(text))
        if hits > best_hits:
            best, best_hits = field, hits
    return best


def _title(text: str) -> str | None:
    sentences = _sentences(text)
    if not sentences:
        return None
    title = _quote(sentences[0])
    if len(title) > TITLE_MAX:
        title = title[:TITLE_MAX].rsplit(" ", 1)[0]
    return title or None


def _users(text: str) -> FieldSuggestion | None:
    labels: list[str] = []
    quotes: list[str] = []
    for match in _USER_WORD_RE.finditer(text):
        stem = match.group(1).lower()
        label = next(label for prefix, label in _USER_LABELS if prefix == stem)
        if label not in labels:
            labels.append(label)
            quotes.append(match.group(0))
    if not labels:
        return None
    labels = labels[:3]
    value = ", ".join([labels[0]] + [label.lower() for label in labels[1:]])
    evidence = [EvidenceOut(source="draft", quote=quote) for quote in quotes[:3]]
    return FieldSuggestion(field="users", value=value, evidence=evidence)


def _contacts(text: str, source: str) -> FieldSuggestion | None:
    matches = [match.group(0).rstrip(".,;") for match in CONTACT_RE.finditer(text)]
    if not matches:
        return None
    return FieldSuggestion(
        field="contact",
        value=", ".join(matches),
        evidence=[EvidenceOut(source=source, quote=match) for match in matches],
    )


def _detect_topic(text: str) -> str | None:
    normalized = normalize(text)
    scores = {topic: len(pattern.findall(normalized)) for topic, pattern in _TOPIC_RULES}
    topic, hits = max(scores.items(), key=lambda item: item[1])
    return topic if hits else None


def _extract(text: str, source: str, allowed: Iterable[str] | None = None) -> dict[str, FieldSuggestion]:
    allowed_set = set(allowed) if allowed is not None else None
    grouped: dict[str, list[str]] = {}
    for clause in _clauses(text):
        field = _classify(clause)
        if field and (allowed_set is None or field in allowed_set):
            grouped.setdefault(field, []).append(clause)

    result = {
        field: FieldSuggestion(
            field=field,
            value=_compose(fragments),
            evidence=[EvidenceOut(source=source, quote=_quote(fragment)) for fragment in fragments],
        )
        for field, fragments in grouped.items()
    }
    if allowed_set is None or "contact" in allowed_set:
        contact = _contacts(text, source)
        if contact:
            result["contact"] = contact
    return result


def _as_card(suggestions: Iterable[FieldSuggestion]) -> dict[str, dict[str, str]]:
    return {item.field: {"value": item.value, "status": "confirmed"} for item in suggestions}


class StubAIService:
    """Детерминированная реализация AIService, всегда успешна."""

    def _meta(self) -> AICallMeta:
        settings = get_settings()
        first_choice = (
            settings.ai_provider if settings.ai_provider != "auto" else next(iter(settings.ai_chain), "stub")
        )
        return AICallMeta(
            provider=STUB_PROVIDER, model=STUB_MODEL, degraded=first_choice != STUB_PROVIDER, trace_ids=[]
        )

    def analyze_draft(
        self, draft: str, topic: str | None, task_id: int | None
    ) -> tuple[DraftAnalysis, AICallMeta]:
        found = _extract(draft, "draft")
        if "users" not in found and (users := _users(draft)):
            found["users"] = users
        title = _title(draft)
        if title:
            found["title"] = FieldSuggestion(
                field="title", value=title, evidence=[EvidenceOut(source="draft", quote=title)]
            )

        missing = [field for field in SCORED_FIELD_KEYS if field not in found]
        probe = _as_card(found.values())
        weak = [field for field in SCORED_FIELD_KEYS if field in found and field_gain(probe, field) > 0]
        questions = select_questions(missing, weak)

        detected = topic if topic in TOPIC_KEYS else _detect_topic(draft)
        analysis = DraftAnalysis(
            fields=list(found.values()), missing=missing, questions=questions, topic=detected
        )
        return analysis, self._meta()

    def build_card(
        self, draft: str, qa: list[QAPair], confirmed: dict[str, str], task_id: int | None
    ) -> tuple[CardBuild, AICallMeta]:
        result = {field: item for field, item in _extract(draft, "draft").items() if field not in confirmed}
        if "users" not in result and "users" not in confirmed and (users := _users(draft)):
            result["users"] = users

        answered: dict[str, list[QAPair]] = {}
        for pair in qa:
            if pair.answer.strip() and pair.field not in confirmed:
                answered.setdefault(pair.field, []).append(pair)

        for field, pairs in answered.items():
            result[field] = FieldSuggestion(
                field=field,
                value=_compose(pair.answer for pair in pairs),
                evidence=[
                    EvidenceOut(source=f"answer:{pair.question_id}", quote=_quote(pair.answer))
                    for pair in pairs
                ],
            )

        for pair in qa:
            if not pair.answer.strip():
                continue
            secondary = _extract(
                pair.answer, f"answer:{pair.question_id}", allowed=_SECONDARY_ANSWER_FIELDS | {"contact"}
            )
            for field, item in secondary.items():
                if field not in confirmed and field not in answered and field not in result:
                    result[field] = item

        unresolved = [field for field in SCORED_FIELD_KEYS if field not in result and field not in confirmed]
        return CardBuild(fields=list(result.values()), unresolved=unresolved), self._meta()
