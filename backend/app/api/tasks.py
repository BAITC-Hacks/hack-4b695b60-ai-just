from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session, select

from app.ai.contracts import AIService
from app.ai.service import get_ai_service
from app.db import get_session
from app.domain.rating import Rating, compute_rating
from app.errors import domain_error, not_found
from app.models import Business, Task
from app.schemas import AnswersIn, CardPatch, PublishIn, ScoreEventOut, TaskCreate, TaskDetail, TaskSummary
from app.services import task_service
from app.services.task_views import get_task_or_404, score_history, task_detail, task_summary

router = APIRouter(prefix="/api", tags=["tasks"])

SessionDep = Annotated[Session, Depends(get_session)]
AIDep = Annotated[AIService, Depends(get_ai_service)]


@router.post("/tasks", response_model=TaskDetail, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, session: SessionDep, ai: AIDep) -> TaskDetail:
    if session.get(Business, payload.business_id) is None:
        raise not_found("BUSINESS_NOT_FOUND", "Бизнес не найден")
    task, _meta = task_service.create_task_from_draft(
        session, business_id=payload.business_id, draft_text=payload.draft_text, topic=payload.topic, ai=ai
    )
    session.commit()
    session.refresh(task)
    return task_detail(session, task, previous_score=0)


@router.get("/tasks", response_model=list[TaskSummary])
def list_tasks(session: SessionDep, business_id: Annotated[int | None, Query()] = None) -> list[TaskSummary]:
    query = select(Task).order_by(Task.updated_at.desc())  # type: ignore[union-attr]
    if business_id is not None:
        query = query.where(Task.business_id == business_id)
    return [task_summary(session, task) for task in session.exec(query).all()]


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_task(task_id: int, session: SessionDep) -> TaskDetail:
    return task_detail(session, get_task_or_404(session, task_id))


@router.post("/tasks/{task_id}/answers", response_model=TaskDetail)
def answer_questions(task_id: int, payload: AnswersIn, session: SessionDep, ai: AIDep) -> TaskDetail:
    task = get_task_or_404(session, task_id)
    before = task.score
    task_service.apply_answers(session, task, ((a.question_id, a.text) for a in payload.answers), ai)
    session.commit()
    session.refresh(task)
    return task_detail(session, task, previous_score=before)


@router.post("/tasks/{task_id}/clarify", response_model=TaskDetail)
def clarify(task_id: int, session: SessionDep) -> TaskDetail:
    task = get_task_or_404(session, task_id)
    task_service.ask_more_questions(session, task)
    session.commit()
    session.refresh(task)
    return task_detail(session, task)


@router.patch("/tasks/{task_id}/card", response_model=TaskDetail)
def patch_card(task_id: int, payload: CardPatch, session: SessionDep) -> TaskDetail:
    task = get_task_or_404(session, task_id)
    before = task.score
    changes = []
    for field, change in payload.fields.items():
        if "value" in change.model_fields_set:
            changes.append((field, "set", change.value))
        elif change.confirm:
            changes.append((field, "confirm", None))
        elif change.reject:
            changes.append((field, "reject", None))
    task_service.patch_card(session, task, changes)
    session.commit()
    session.refresh(task)
    return task_detail(session, task, previous_score=before)


@router.post("/tasks/{task_id}/confirm-all", response_model=TaskDetail)
def confirm_all(task_id: int, session: SessionDep) -> TaskDetail:
    task = get_task_or_404(session, task_id)
    before = task.score
    task_service.confirm_all(session, task)
    session.commit()
    session.refresh(task)
    return task_detail(session, task, previous_score=before)


@router.get("/tasks/{task_id}/rating", response_model=Rating)
def get_rating(task_id: int, session: SessionDep) -> Rating:
    return compute_rating(get_task_or_404(session, task_id).card)


@router.get("/tasks/{task_id}/history", response_model=list[ScoreEventOut])
def get_history(task_id: int, session: SessionDep) -> list[ScoreEventOut]:
    get_task_or_404(session, task_id)
    return score_history(session, task_id)


@router.post("/tasks/{task_id}/publish", response_model=TaskDetail)
def publish(task_id: int, payload: PublishIn, session: SessionDep) -> TaskDetail:
    if not payload.confirm:
        raise domain_error(
            status.HTTP_400_BAD_REQUEST, "CONFIRMATION_REQUIRED", "Подтвердите, что проверили карточку"
        )
    task = get_task_or_404(session, task_id)
    before = task.score
    task_service.publish_task(session, task)
    session.commit()
    session.refresh(task)
    return task_detail(session, task, previous_score=before)
