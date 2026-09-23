"""Общий каталог: все опубликованные задачи, позиция по рейтингу, фильтры только по явному выбору."""

from collections.abc import Collection, Mapping
from typing import Literal

from sqlmodel import Session, select

from app.domain.catalog import RankEntry, positions
from app.domain.fields import FIELD_KEYS, level_for
from app.domain.rating import Level, compute_rating, counted_value, normalize
from app.errors import not_found
from app.models import Business, Task
from app.schemas import CatalogItem, CatalogPage, PublicTask
from app.services.task_views import proposals_count

NEED_PREVIEW_MAX = 160


def level_model(score: int) -> Level:
    level = level_for(score)
    return Level(key=level.key, label=level.label, min=level.min, max=level.max)


def published_tasks(session: Session) -> list[Task]:
    return list(session.exec(select(Task).where(Task.status == "published")).all())


def catalog_positions(tasks: Collection[Task]) -> dict[int, int]:
    return positions(
        RankEntry(id=task.id, score=task.score, published_at=task.published_at) for task in tasks
    )


def business_names(session: Session) -> dict[int, str]:
    return {business.id: business.name for business in session.exec(select(Business)).all()}


def task_title(task: Task) -> str:
    return counted_value(task.card, "title") or (task.card.get("title") or {}).get("value") or "Без названия"


def _preview(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) <= NEED_PREVIEW_MAX:
        return compact
    return compact[: NEED_PREVIEW_MAX - 1].rstrip() + "…"


def _matches(task: Task, query: str) -> bool:
    parts = (counted_value(task.card, key) for key in ("title", "need", "context"))
    return normalize(query) in normalize(" ".join(part for part in parts if part))


def catalog_item(session: Session, task: Task, position: int, names: Mapping[int, str]) -> CatalogItem:
    level = level_model(task.score)
    need = counted_value(task.card, "need") or counted_value(task.card, "context") or ""
    return CatalogItem(
        id=task.id,
        title=task_title(task),
        topic=task.topic,
        business_name=names.get(task.business_id, ""),
        score=task.score,
        level=level,
        highlighted=level.key == "priority",
        needs_clarification=level.key == "draft",
        need_preview=_preview(need),
        proposals_count=proposals_count(session, task.id),
        position=position,
        published_at=task.published_at,
    )


def list_catalog(
    session: Session,
    *,
    topic: str | None,
    levels: Collection[str],
    query: str | None,
    sort: Literal["rating", "newest"],
    limit: int,
    offset: int,
) -> CatalogPage:
    tasks = published_tasks(session)
    ranks = catalog_positions(tasks)
    filtered = [
        task
        for task in tasks
        if (topic is None or task.topic == topic)
        and (not levels or level_for(task.score).key in levels)
        and (not query or _matches(task, query))
    ]
    if sort == "newest":
        filtered.sort(key=lambda task: (task.published_at, task.id), reverse=True)
    else:
        filtered.sort(key=lambda task: ranks[task.id])
    names = business_names(session)
    items = [catalog_item(session, task, ranks[task.id], names) for task in filtered[offset : offset + limit]]
    return CatalogPage(items=items, total=len(filtered))


def get_published_or_404(session: Session, task_id: int) -> Task:
    task = session.get(Task, task_id)
    if task is None or task.status != "published":
        raise not_found("TASK_NOT_FOUND", "Задача не найдена в каталоге")
    return task


def public_task(session: Session, task: Task) -> PublicTask:
    ranks = catalog_positions(published_tasks(session))
    card = {key: value for key in FIELD_KEYS if (value := counted_value(task.card, key))}
    return PublicTask(
        id=task.id,
        title=task_title(task),
        topic=task.topic,
        business_name=business_names(session).get(task.business_id, ""),
        card=card,
        rating=compute_rating(task.card),
        position=ranks[task.id],
        proposals_count=proposals_count(session, task.id),
        published_at=task.published_at,
    )
