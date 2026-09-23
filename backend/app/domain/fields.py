from dataclasses import dataclass
from typing import Literal, get_args

FieldKey = Literal[
    "title",
    "context",
    "need",
    "users",
    "data",
    "constraints",
    "expected_result",
    "success_criteria",
    "contact",
    "interaction_format",
]
CriterionKey = Literal[
    "context_need", "data", "expected_result", "success_criteria", "constraints", "users", "business_link"
]
LevelKey = Literal["draft", "working", "ready", "priority"]

FIELD_KEYS: tuple[FieldKey, ...] = get_args(FieldKey)
SCORED_FIELD_KEYS: tuple[FieldKey, ...] = tuple(key for key in FIELD_KEYS if key != "title")


@dataclass(frozen=True)
class FieldDef:
    key: FieldKey
    label: str
    criterion: CriterionKey | None
    placeholder: str


@dataclass(frozen=True)
class CriterionDef:
    key: CriterionKey
    label: str
    weight: int
    description: str


@dataclass(frozen=True)
class LevelDef:
    key: LevelKey
    label: str
    min: int
    max: int


FIELDS: tuple[FieldDef, ...] = (
    FieldDef("title", "Название", None, "Коротко: что нужно сделать"),
    FieldDef("context", "Контекст", "context_need", "Что происходит сейчас: процесс, проблема, масштаб"),
    FieldDef("need", "Потребность", "context_need", "Что должно измениться после работы команды"),
    FieldDef("users", "Пользователи", "users", "Кто будет пользоваться решением: роли, отделы, сегменты"),
    FieldDef("data", "Данные и материалы", "data", "Какие данные, примеры и доступы есть, формат и объём"),
    FieldDef("constraints", "Ограничения", "constraints", "Сроки, обязательные технологии, доступы, бюджет"),
    FieldDef("expected_result", "Ожидаемый результат", "expected_result", "Что именно должна сдать команда"),
    FieldDef(
        "success_criteria", "Критерии успеха", "success_criteria", "Измеримые признаки приёмки результата"
    ),
    FieldDef("contact", "Контакт", "business_link", "Имя и роль, email, телефон или @telegram"),
    FieldDef(
        "interaction_format",
        "Формат взаимодействия",
        "business_link",
        "Как часто и где вы консультируете команду и даёте обратную связь",
    ),
)

CRITERIA: tuple[CriterionDef, ...] = (
    CriterionDef(
        "context_need",
        "Контекст и потребность",
        20,
        "Понятно, что происходит сейчас и что необходимо изменить",
    ),
    CriterionDef("data", "Данные и материалы", 20, "Указаны доступные данные, примеры или источники"),
    CriterionDef("expected_result", "Ожидаемый результат", 15, "Описан конкретный результат работы команды"),
    CriterionDef("success_criteria", "Критерии успеха", 15, "Есть измеримые признаки принятия решения"),
    CriterionDef("constraints", "Ограничения", 10, "Указаны сроки, технологии, доступы или иные границы"),
    CriterionDef("users", "Пользователи", 10, "Понятно, для кого создаётся решение"),
    CriterionDef(
        "business_link", "Связь с бизнесом", 10, "Есть контакт, формат консультаций и порядок обратной связи"
    ),
)

LEVELS: tuple[LevelDef, ...] = (
    LevelDef("draft", "Черновик", 0, 39),
    LevelDef("working", "Рабочая", 40, 69),
    LevelDef("ready", "Готовая", 70, 89),
    LevelDef("priority", "Приоритетная", 90, 100),
)

TOPICS: tuple[tuple[str, str], ...] = (
    ("retail", "Ритейл"),
    ("logistics", "Логистика"),
    ("finance", "Финансы"),
    ("education", "Образование"),
    ("healthcare", "Здравоохранение"),
    ("agro", "Агро"),
    ("government", "Госсектор"),
    ("manufacturing", "Производство"),
    ("it_telecom", "IT и телеком"),
    ("other", "Другое"),
)

TOPIC_KEYS: frozenset[str] = frozenset(key for key, _ in TOPICS)
FIELD_LABELS: dict[str, str] = {field.key: field.label for field in FIELDS}
LEVELS_BY_KEY: dict[str, LevelDef] = {level.key: level for level in LEVELS}


def level_for(score: int) -> LevelDef:
    for level in LEVELS:
        if level.min <= score <= level.max:
            return level
    return LEVELS[0] if score < 0 else LEVELS[-1]


def next_level(score: int) -> LevelDef | None:
    current = level_for(score)
    index = LEVELS.index(current)
    return LEVELS[index + 1] if index + 1 < len(LEVELS) else None
