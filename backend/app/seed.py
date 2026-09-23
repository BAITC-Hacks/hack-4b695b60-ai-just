"""Загрузка синтетических данных из data/seed. Все компании, люди и контакты вымышлены."""

import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.ai.stub import StubAIService
from app.config import get_settings
from app.db import create_tables, drop_tables, engine
from app.domain.card import empty_card, user_field
from app.models import Business, Milestone, Proposal, Task, Team, utcnow
from app.services.task_service import create_task_from_draft, recalculate

logger = logging.getLogger(__name__)


def _read(seed_dir: Path, name: str) -> list[dict[str, Any]]:
    return json.loads((seed_dir / name).read_text(encoding="utf-8"))


def seed_database(session: Session, seed_dir: Path) -> None:
    now = utcnow()

    businesses: dict[str, Business] = {}
    for item in _read(seed_dir, "businesses.json"):
        business = Business(name=item["name"], industry=item.get("industry"))
        session.add(business)
        businesses[item["key"]] = business

    teams: dict[str, Team] = {}
    for item in _read(seed_dir, "teams.json"):
        team = Team(
            name=item["name"],
            interests=item["interests"],
            skills=item["skills"],
            technologies=item["technologies"],
        )
        session.add(team)
        teams[item["key"]] = team
    session.flush()

    tasks: dict[str, Task] = {}
    for item in _read(seed_dir, "cards.json"):
        published_at = now - timedelta(days=item.get("published_days_ago", 1))
        card = empty_card()
        for field, value in item["card"].items():
            card[field] = user_field(value, published_at)
        task = Task(
            business_id=businesses[item["business"]].id,
            status="published",
            topic=item.get("topic"),
            draft_text=item["draft_text"],
            card=card,
            created_at=published_at - timedelta(hours=3),
            published_at=published_at,
        )
        session.add(task)
        session.flush()
        recalculate(session, task, reason="Карточка заполнена и опубликована")
        tasks[item["key"]] = task

    stub = StubAIService()
    for item in _read(seed_dir, "drafts.json"):
        create_task_from_draft(
            session,
            business_id=businesses[item["business"]].id,
            draft_text=item["draft_text"],
            topic=item.get("topic"),
            ai=stub,
        )

    proposals: dict[str, Proposal] = {}
    for item in _read(seed_dir, "proposals.json"):
        task = tasks[item["task"]]
        created_at = (task.published_at or now) + timedelta(hours=item.get("hours_after_publish", 6))
        status = item.get("status", "submitted")
        proposal = Proposal(
            task_id=task.id,
            team_id=teams[item["team"]].id,
            idea=item["idea"],
            plan=item["plan"],
            timeline=item["timeline"],
            prototype_url=item.get("prototype_url"),
            status=status,
            business_comment=item.get("business_comment"),
            created_at=created_at,
            decided_at=created_at + timedelta(hours=12) if status != "submitted" else None,
        )
        session.add(proposal)
        proposals[item["key"]] = proposal
    session.flush()

    for item in _read(seed_dir, "milestones.json"):
        proposal = proposals[item["proposal"]]
        confirmed = item.get("status") == "confirmed"
        confirmed_at = (proposal.decided_at or now) + timedelta(days=1) if confirmed else None
        session.add(
            Milestone(
                proposal_id=proposal.id,
                title=item["title"],
                points=item.get("points", 10),
                status="confirmed" if confirmed else "pending",
                confirmed_at=confirmed_at,
            )
        )
        if confirmed:
            team = session.get(Team, proposal.team_id)
            team.progress_points += item.get("points", 10)
            team.last_points_at = confirmed_at
            session.add(team)

    session.commit()
    logger.info("Seed loaded from %s", seed_dir)


def reset_and_seed() -> None:
    drop_tables()
    create_tables()
    with Session(engine) as session:
        seed_database(session, get_settings().seed_dir)


def ensure_seeded() -> None:
    create_tables()
    with Session(engine) as session:
        if session.exec(select(Business)).first() is None:
            seed_database(session, get_settings().seed_dir)
