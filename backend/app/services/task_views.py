"""Сборка ответов API по задаче: карточка, вопросы, рейтинг, позиция в каталоге."""

from sqlalchemy import func
from sqlmodel import Session, select

from app.domain.card import normalize_card
from app.domain.catalog import RankEntry, position_preview, positions
from app.domain.rating import Level, compute_rating, field_gain
from app.errors import not_found
from app.models import Business, Proposal, ScoreEvent, Task, utcnow
from app.schemas import AiMeta, BusinessRef, CardDTO, QuestionDTO, ScoreEventOut, TaskDetail, TaskSummary
from app.services.task_service import task_questions


def get_task_or_404(session: Session, task_id: int) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise not_found("TASK_NOT_FOUND", "Задача не найдена")
    return task


def published_entries(session: Session) -> list[RankEntry]:
    rows = session.exec(
        select(Task.id, Task.score, Task.published_at).where(Task.status == "published")
    ).all()
    return [RankEntry(id=row[0], score=row[1], published_at=row[2]) for row in rows if row[2] is not None]


def proposals_count(session: Session, task_id: int) -> int:
    return session.exec(select(func.count()).select_from(Proposal).where(Proposal.task_id == task_id)).one()


def task_detail(session: Session, task: Task, *, previous_score: int | None = None) -> TaskDetail:
    """previous_score передаётся из изменяющих эндпоинтов, чтобы rating.delta показал эффект действия."""
    card = normalize_card(task.card)
    entries = published_entries(session)
    business = session.get(Business, task.business_id)
    questions = [
        QuestionDTO(
            id=q.key,
            field=q.field,
            question=q.question,
            why=q.why,
            points_gain=field_gain(card, q.field),
            answer=q.answer,
            round=q.round,
        )
        for q in task_questions(session, task.id)
    ]
    return TaskDetail(
        id=task.id,
        business=BusinessRef(id=business.id, name=business.name),
        status=task.status,
        topic=task.topic,
        draft_text=task.draft_text,
        card=CardDTO.model_validate(card),
        questions=questions,
        rating=compute_rating(card, previous_score=previous_score),
        catalog_position=positions(entries).get(task.id) if task.status == "published" else None,
        catalog_position_preview=position_preview(
            task.score, entries, task_id=task.id, published_at=task.published_at, now=utcnow()
        ),
        proposals_count=proposals_count(session, task.id),
        ai=AiMeta.model_validate(task.ai_meta) if task.ai_meta else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
        published_at=task.published_at,
    )


def task_summary(session: Session, task: Task) -> TaskSummary:
    rating = compute_rating(task.card)
    title = (task.card.get("title") or {}).get("value")
    return TaskSummary(
        id=task.id,
        title=title,
        status=task.status,
        topic=task.topic,
        score=rating.score,
        level=Level.model_validate(rating.level.model_dump()),
        proposals_count=proposals_count(session, task.id),
        updated_at=task.updated_at,
    )


def score_history(session: Session, task_id: int) -> list[ScoreEventOut]:
    events = session.exec(
        select(ScoreEvent).where(ScoreEvent.task_id == task_id).order_by(ScoreEvent.id)
    ).all()
    return [ScoreEventOut.model_validate(event) for event in events]
