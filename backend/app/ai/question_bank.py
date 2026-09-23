from collections.abc import Iterable

from app.ai.contracts import QuestionOut
from app.domain.fields import FieldKey

MIN_QUESTIONS = 3
MAX_QUESTIONS = 5

QUESTION_PRIORITY: tuple[FieldKey, ...] = (
    "data",
    "context",
    "need",
    "expected_result",
    "success_criteria",
    "constraints",
    "users",
    "contact",
    "interaction_format",
)

BANK: dict[str, tuple[str, str]] = {
    "data": (
        "Какие данные или материалы вы можете дать команде (выгрузки, документы, примеры) "
        "и в каком формате и объёме?",
        "Без данных команда не сможет начать работу",
    ),
    "context": (
        "Что происходит сейчас: как устроен процесс и в чём главная проблема?",
        "Команде нужно понимать текущую ситуацию и масштаб",
    ),
    "need": (
        "Что именно должно измениться после работы команды?",
        "Так команда поймёт цель, а не только задачу",
    ),
    "expected_result": (
        "Какой результат вы хотите получить: прототип, бот, дашборд, исследование?",
        "Команде нужно понимать, что именно сдавать",
    ),
    "success_criteria": (
        "По каким измеримым признакам вы примете результат (процент, время, количество)?",
        "Нужен понятный критерий приёмки",
    ),
    "constraints": (
        "Есть ли ограничения: сроки, обязательные технологии, доступы, бюджет?",
        "Ограничения влияют на выбор решения",
    ),
    "users": (
        "Кто будет пользоваться решением: какие роли или группы людей?",
        "Решение делают под конкретных людей",
    ),
    "contact": (
        "Кто будет контактным лицом со стороны бизнеса и как с ним связаться?",
        "Команде нужно знать, к кому обращаться с вопросами",
    ),
    "interaction_format": (
        "Как часто и в каком формате вы готовы консультировать команду и давать обратную связь?",
        "Регулярная обратная связь снижает риск сделать не то",
    ),
}


def bank_question(field: FieldKey) -> QuestionOut:
    question, why = BANK[field]
    return QuestionOut(field=field, question=question, why=why)


def select_questions(
    missing: Iterable[str],
    weak: Iterable[str] = (),
    exclude: Iterable[str] = (),
    *,
    minimum: int = MIN_QUESTIONS,
    maximum: int = MAX_QUESTIONS,
) -> list[QuestionOut]:
    """Сначала пустые поля, потом слабые, потом остальные — в порядке веса. От minimum до maximum вопросов."""
    excluded, missing_set, weak_set = set(exclude), set(missing), set(weak)
    candidates = [field for field in QUESTION_PRIORITY if field not in excluded]
    ordered = [field for field in candidates if field in missing_set]
    ordered += [field for field in candidates if field in weak_set and field not in ordered]
    if len(ordered) < minimum:
        ordered += [field for field in candidates if field not in ordered][: minimum - len(ordered)]
    return [bank_question(field) for field in ordered[:maximum]]
