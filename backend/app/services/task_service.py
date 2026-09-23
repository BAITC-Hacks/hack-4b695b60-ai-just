"""Сценарии задачи поверх domain/ и AIService: создание, ответы, правки, публикация, пересчёт рейтинга."""

from collections.abc import Iterable, Mapping
from typing import Any, Literal

from fastapi import status
from sqlmodel import Session, select

from app.ai.contracts import AICallMeta, AIService, FieldSuggestion, QAPair, QuestionOut
from app.ai.question_bank import MAX_QUESTIONS, MIN_QUESTIONS, select_questions
from app.domain.card import (
    apply_suggestions,
    confirm_field,
    confirmed_values,
    empty_card,
    reject_field,
    set_user_value,
    suggested_fields,
)
from app.domain.fields import FIELD_LABELS, SCORED_FIELD_KEYS, TOPIC_KEYS
from app.domain.rating import Rating, compute_rating, counted_value, field_gain
from app.errors import domain_error, not_found
from app.models import Question, ScoreEvent, Task, utcnow

FieldAction = Literal["set", "confirm", "reject"]


def suggestions_to_tuples(fields: Iterable[FieldSuggestion]) -> list[tuple[str, str, list[dict[str, str]]]]:
    return [
        (item.field, item.value, [{"source": ev.source, "quote": ev.quote} for ev in item.evidence])
        for item in fields
    ]


def store_ai_meta(task: Task, meta: AICallMeta) -> None:
    task.ai_meta = {
        "provider_used": meta.provider,
        "model": meta.model,
        "degraded": meta.degraded,
        "trace_ids": list(meta.trace_ids),
    }


def last_score(session: Session, task_id: int) -> int | None:
    event = session.exec(
        select(ScoreEvent).where(ScoreEvent.task_id == task_id).order_by(ScoreEvent.id.desc())  # type: ignore[union-attr]
    ).first()
    return event.score if event else None


def recalculate(session: Session, task: Task, reason: str, *, force_event: bool = False) -> Rating:
    """Пересчитывает рейтинг; score_event пишется при изменении балла, первом расчёте или по требованию."""
    previous = last_score(session, task.id) if task.id is not None else None
    rating = compute_rating(task.card, previous_score=previous)
    task.score = rating.score
    task.potential_score = rating.potential_score
    task.level = rating.level.key
    task.updated_at = utcnow()
    session.add(task)
    if previous is None or rating.score != previous or force_event:
        session.add(
            ScoreEvent(
                task_id=task.id,
                score=rating.score,
                delta=rating.score - (previous or 0),
                level=rating.level.key,
                reason=reason,
            )
        )
    return rating


def task_questions(session: Session, task_id: int) -> list[Question]:
    return list(session.exec(select(Question).where(Question.task_id == task_id).order_by(Question.id)).all())


def add_questions(
    session: Session, task: Task, questions: list[QuestionOut], round_number: int
) -> list[Question]:
    start = len(task_questions(session, task.id)) + 1
    created = [
        Question(
            task_id=task.id,
            key=f"q{start + offset}",
            field=item.field,
            question=item.question,
            why=item.why,
            points_gain=field_gain(task.card, item.field),
            round=round_number,
        )
        for offset, item in enumerate(questions)
    ]
    session.add_all(created)
    return created


def field_gaps(card: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Пустые поля и заполненные, но недобравшие баллы; предложения AI считаем принятыми."""
    probe = {
        key: ({**entry, "status": "confirmed"} if entry.get("status") == "suggested" else entry)
        for key, entry in card.items()
    }
    missing = [key for key in SCORED_FIELD_KEYS if (card.get(key) or {}).get("status", "empty") == "empty"]
    weak = [key for key in SCORED_FIELD_KEYS if key not in missing and field_gain(probe, key) > 0]
    return missing, weak


def create_task_from_draft(
    session: Session, *, business_id: int, draft_text: str, topic: str | None, ai: AIService
) -> tuple[Task, AICallMeta]:
    task = Task(
        business_id=business_id,
        draft_text=draft_text.strip(),
        topic=topic if topic in TOPIC_KEYS else None,
    )
    session.add(task)
    session.flush()

    analysis, meta = ai.analyze_draft(task.draft_text, task.topic, task.id)
    card, _changed = apply_suggestions(empty_card(), suggestions_to_tuples(analysis.fields), utcnow())
    task.card = card
    if task.topic is None and analysis.topic in TOPIC_KEYS:
        task.topic = analysis.topic
    task.status = "clarifying"
    store_ai_meta(task, meta)

    add_questions(session, task, analysis.questions, round_number=1)
    recalculate(session, task, reason="Задача создана из черновика")
    return task, meta


def apply_answers(session: Session, task: Task, answers: Iterable[tuple[str, str]], ai: AIService) -> None:
    questions = {question.key: question for question in task_questions(session, task.id)}
    answered_now = 0
    for key, text in answers:
        question = questions.get(key)
        if question is None:
            raise not_found("QUESTION_NOT_FOUND", f"Вопрос {key} не найден в этой задаче")
        question.answer = text.strip() or None
        answered_now += bool(question.answer)
        session.add(question)

    qa = [
        QAPair(question_id=q.key, field=q.field, question=q.question, answer=q.answer)
        for q in questions.values()
        if q.answer
    ]
    build, meta = ai.build_card(task.draft_text, qa, confirmed_values(task.card), task.id)
    task.card, _changed = apply_suggestions(task.card, suggestions_to_tuples(build.fields), utcnow())
    if task.status == "clarifying":
        task.status = "review"
    store_ai_meta(task, meta)
    recalculate(session, task, reason=f"Применены ответы на вопросы: {answered_now}")


def ask_more_questions(session: Session, task: Task) -> list[Question]:
    """Новый раунд по оставшимся пробелам; поля с открытыми вопросами не дублируем."""
    existing = task_questions(session, task.id)
    open_fields = {q.field for q in existing if not q.answer}
    missing, weak = field_gaps(task.card)
    gaps = [field for field in (*missing, *weak) if field not in open_fields]
    if not gaps:
        return []
    questions = select_questions(
        missing,
        weak,
        exclude=open_fields,
        minimum=min(MIN_QUESTIONS, len(gaps)),
        maximum=MAX_QUESTIONS,
    )
    round_number = max((q.round for q in existing), default=0) + 1
    return add_questions(session, task, questions, round_number)


def patch_card(session: Session, task: Task, changes: Iterable[tuple[str, FieldAction, str | None]]) -> None:
    now = utcnow()
    card = task.card
    labels: dict[FieldAction, list[str]] = {"set": [], "confirm": [], "reject": []}
    for field, action, value in changes:
        if action == "set":
            card = set_user_value(card, field, value, now)
        elif action == "confirm":
            card = confirm_field(card, field, now)
        else:
            card = reject_field(card, field, now)
        labels[action].append(FIELD_LABELS[field])
    task.card = card
    if task.status == "clarifying":
        task.status = "review"

    titles = {"set": "Изменено", "confirm": "Подтверждено", "reject": "Отклонено"}
    reason = "; ".join(f"{titles[action]}: {', '.join(names)}" for action, names in labels.items() if names)
    recalculate(session, task, reason=reason or "Карточка обновлена")


def confirm_all(session: Session, task: Task) -> None:
    fields = suggested_fields(task.card)
    if not fields:
        return
    now = utcnow()
    card = task.card
    for field in fields:
        card = confirm_field(card, field, now)
    task.card = card
    if task.status == "clarifying":
        task.status = "review"
    recalculate(
        session, task, reason=f"Подтверждены предложения AI: {', '.join(FIELD_LABELS[f] for f in fields)}"
    )


def publish_task(session: Session, task: Task) -> None:
    if counted_value(task.card, "title") is None:
        raise domain_error(
            status.HTTP_409_CONFLICT, "TITLE_REQUIRED", "Подтвердите название задачи перед публикацией"
        )
    if task.status != "published":
        task.status = "published"
        task.published_at = utcnow()
    recalculate(session, task, reason="Задача опубликована в каталоге", force_event=True)
