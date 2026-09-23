"""Recommendations only; the public catalog remains unrestricted."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.db import get_session
from app.domain.card import confirmed_values
from app.domain.catalog import RankEntry, positions
from app.domain.fields import LEVELS_BY_KEY
from app.errors import not_found
from app.ml.recommend import recommend
from app.models import Business, Proposal, Task, Team

router = APIRouter(prefix="/api", tags=["recommendations"])
SessionDep = Annotated[Session, Depends(get_session)]
NOTE = "Рекомендации не ограничивают каталог: все задачи доступны во вкладке «Каталог»"


@router.get("/teams/{team_id}/recommendations")
def team_recommendations(
    team_id: int, session: SessionDep, limit: int = Query(5, ge=1, le=50)
) -> dict[str, Any]:
    team = session.get(Team, team_id)
    if team is None:
        raise not_found("TEAM_NOT_FOUND", "Команда не найдена")
    tasks = list(session.exec(select(Task).where(Task.status == "published")).all())
    recommendations, method = recommend(team, tasks, limit)
    ranks = positions(
        RankEntry(id=task.id, score=task.score, published_at=task.published_at) for task in tasks
    )
    business_ids = {task.business_id for task in tasks}
    businesses = {
        business.id: business.name
        for business in session.exec(select(Business).where(Business.id.in_(business_ids))).all()
    }
    counts: dict[int, int] = {}
    for proposal in session.exec(
        select(Proposal).where(Proposal.task_id.in_([task.id for task in tasks]))
    ).all():
        counts[proposal.task_id] = counts.get(proposal.task_id, 0) + 1
    items = []
    for item in recommendations:
        task = item["task"]
        fields = confirmed_values(task.card)
        level = LEVELS_BY_KEY[task.level]
        items.append(
            {
                "task": {
                    "id": task.id,
                    "title": fields.get("title") or f"Задача №{task.id}",
                    "topic": task.topic,
                    "business_name": businesses.get(task.business_id, ""),
                    "score": task.score,
                    "level": {"key": level.key, "label": level.label, "min": level.min, "max": level.max},
                    "highlighted": task.level == "priority",
                    "needs_clarification": task.level == "draft",
                    "need_preview": (fields.get("need") or "")[:160],
                    "proposals_count": counts.get(task.id, 0),
                    "position": ranks[task.id],
                    "published_at": task.published_at.isoformat() + "Z",
                },
                "match": item["match"],
                "reasons": item["reasons"],
                "matched_terms": item["matched_terms"],
            }
        )
    return {"items": items, "method": method, "note": NOTE}
