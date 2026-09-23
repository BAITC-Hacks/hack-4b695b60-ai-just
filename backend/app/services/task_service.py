"""Сценарии задачи поверх domain/ и AIService: создание, пересчёт рейтинга, история."""

from collections.abc import Iterable

from sqlmodel import Session, select

from app.ai.contracts import AICallMeta, AIService, FieldSuggestion, QuestionOut
from app.domain.card import apply_suggestions, empty_card
from app.domain.fields import TOPIC_KEYS
from app.domain.rating import Rating, compute_rating, field_gain
from app.models import Question, ScoreEvent, Task, utcnow


def suggestions_to_tuples(fields: Iterable[FieldSuggestion]) -> list[tuple[str, str, list[dict[str, str]]]]:
    return [
        (item.field, item.value, [{"source": ev.source, "quote": ev.quote} for ev in item.evidence])
        for item in fields
    ]


def last_score(session: Session, task_id: int) -> int | None:
    event = session.exec(
        select(ScoreEvent).where(ScoreEvent.task_id == task_id).order_by(ScoreEvent.id.desc())  # type: ignore[union-attr]
    ).first()
    return event.score if event else None


def recalculate(session: Session, task: Task, reason: str) -> Rating:
    """Пересчитывает рейтинг и пишет score_event, если балл изменился (или это первый расчёт)."""
    previous = last_score(session, task.id) if task.id is not None else None
    rating = compute_rating(task.card, previous_score=previous)
    task.score = rating.score
    task.potential_score = rating.potential_score
    task.level = rating.level.key
    task.updated_at = utcnow()
    session.add(task)
    if previous is None or rating.score != previous:
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


def next_question_keys(session: Session, task_id: int, count: int) -> list[str]:
    existing = session.exec(select(Question.key).where(Question.task_id == task_id)).all()
    start = len(existing) + 1
    return [f"q{index}" for index in range(start, start + count)]


def add_questions(
    session: Session, task: Task, questions: list[QuestionOut], round_number: int
) -> list[Question]:
    keys = next_question_keys(session, task.id, len(questions))
    created = [
        Question(
            task_id=task.id,
            key=key,
            field=item.field,
            question=item.question,
            why=item.why,
            points_gain=field_gain(task.card, item.field),
            round=round_number,
        )
        for key, item in zip(keys, questions, strict=True)
    ]
    session.add_all(created)
    return created


def create_task_from_draft(
    session: Session, *, business_id: int, draft_text: str, topic: str | None, ai: AIService
) -> tuple[Task, AICallMeta]:
    task = Task(
        business_id=business_id, draft_text=draft_text.strip(), topic=topic if topic in TOPIC_KEYS else None
    )
    session.add(task)
    session.flush()

    analysis, meta = ai.analyze_draft(task.draft_text, task.topic, task.id)
    card, _changed = apply_suggestions(empty_card(), suggestions_to_tuples(analysis.fields), utcnow())
    task.card = card
    if task.topic is None and analysis.topic in TOPIC_KEYS:
        task.topic = analysis.topic
    task.status = "clarifying"

    add_questions(session, task, analysis.questions, round_number=1)
    recalculate(session, task, reason="Задача создана из черновика")
    return task, meta
