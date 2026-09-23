"""Отклики команд, ручное решение бизнеса и этапы. Автоназначения команд нет и быть не должно."""

from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import func
from sqlmodel import Session, select

from app.errors import domain_error, not_found
from app.models import Business, Milestone, Proposal, Task, Team, utcnow
from app.schemas import (
    BusinessLeaderboard,
    BusinessOut,
    BusinessRank,
    MilestoneOut,
    ProposalOut,
    TaskRef,
    TeamLeaderboard,
    TeamOut,
    TeamRank,
)
from app.services.catalog_views import task_title

_NEVER = datetime.max.replace(tzinfo=UTC)


def get_team_or_404(session: Session, team_id: int) -> Team:
    team = session.get(Team, team_id)
    if team is None:
        raise not_found("TEAM_NOT_FOUND", "Команда не найдена")
    return team


def get_proposal_or_404(session: Session, proposal_id: int) -> Proposal:
    proposal = session.get(Proposal, proposal_id)
    if proposal is None:
        raise not_found("PROPOSAL_NOT_FOUND", "Отклик не найден")
    return proposal


def get_milestone_or_404(session: Session, milestone_id: int) -> Milestone:
    milestone = session.get(Milestone, milestone_id)
    if milestone is None:
        raise not_found("MILESTONE_NOT_FOUND", "Этап не найден")
    return milestone


def ensure_owner(task: Task, business_id: int) -> None:
    if task.business_id != business_id:
        raise domain_error(
            status.HTTP_403_FORBIDDEN, "NOT_TASK_OWNER", "Действие доступно только бизнесу — владельцу задачи"
        )


def ensure_selected(proposal: Proposal) -> None:
    if proposal.status != "selected":
        raise domain_error(
            status.HTTP_409_CONFLICT, "PROPOSAL_NOT_SELECTED", "Этапы доступны только для выбранного отклика"
        )


def create_proposal(
    session: Session,
    task: Task,
    team: Team,
    *,
    idea: str,
    plan: str,
    timeline: str,
    prototype_url: str | None,
) -> Proposal:
    if task.status != "published":
        raise domain_error(
            status.HTTP_409_CONFLICT,
            "TASK_NOT_PUBLISHED",
            "Откликнуться можно только на опубликованную задачу",
        )
    proposal = Proposal(
        task_id=task.id,
        team_id=team.id,
        idea=idea.strip(),
        plan=plan.strip(),
        timeline=timeline.strip(),
        prototype_url=prototype_url,
    )
    session.add(proposal)
    return proposal


def decide(proposal: Proposal, decision: str, comment: str | None) -> None:
    proposal.status = decision
    proposal.business_comment = comment.strip() if comment and comment.strip() else None
    proposal.decided_at = utcnow()


def add_milestone(session: Session, proposal: Proposal, title: str, points: int) -> Milestone:
    ensure_selected(proposal)
    milestone = Milestone(proposal_id=proposal.id, title=title.strip(), points=points)
    session.add(milestone)
    return milestone


def confirm_milestone(session: Session, milestone: Milestone, proposal: Proposal) -> Team:
    if milestone.status == "confirmed":
        raise domain_error(status.HTTP_409_CONFLICT, "MILESTONE_ALREADY_CONFIRMED", "Этап уже подтверждён")
    ensure_selected(proposal)
    now = utcnow()
    milestone.status = "confirmed"
    milestone.confirmed_at = now
    team = session.get(Team, proposal.team_id)
    team.progress_points += milestone.points
    team.last_points_at = now
    session.add_all([milestone, team])
    return team


def proposal_out(session: Session, proposal: Proposal) -> ProposalOut:
    task = session.get(Task, proposal.task_id)
    team = session.get(Team, proposal.team_id)
    milestones = session.exec(
        select(Milestone).where(Milestone.proposal_id == proposal.id).order_by(Milestone.id)
    ).all()
    return ProposalOut(
        id=proposal.id,
        task=TaskRef(id=task.id, title=task_title(task)),
        team=TeamOut.model_validate(team),
        idea=proposal.idea,
        plan=proposal.plan,
        timeline=proposal.timeline,
        prototype_url=proposal.prototype_url,
        status=proposal.status,
        business_comment=proposal.business_comment,
        milestones=[MilestoneOut.model_validate(item) for item in milestones],
        created_at=proposal.created_at,
        decided_at=proposal.decided_at,
    )


def proposals_for_task(session: Session, task_id: int) -> list[Proposal]:
    """Хронологический порядок: система не ранжирует отклики за бизнес."""
    query = select(Proposal).where(Proposal.task_id == task_id).order_by(Proposal.created_at, Proposal.id)
    return list(session.exec(query).all())


def proposals_for_team(session: Session, team_id: int) -> list[Proposal]:
    query = select(Proposal).where(Proposal.team_id == team_id).order_by(Proposal.created_at.desc())  # type: ignore[union-attr]
    return list(session.exec(query).all())


def team_leaderboard(session: Session) -> TeamLeaderboard:
    confirmed = dict(
        session.exec(
            select(Proposal.team_id, func.count(Milestone.id))
            .join(Milestone, Milestone.proposal_id == Proposal.id)
            .where(Milestone.status == "confirmed")
            .group_by(Proposal.team_id)
        ).all()
    )
    teams = sorted(
        session.exec(select(Team)).all(),
        key=lambda team: (-team.progress_points, team.last_points_at or _NEVER, team.id),
    )
    return TeamLeaderboard(
        items=[
            TeamRank(
                rank=rank, team=TeamOut.model_validate(team), confirmed_milestones=confirmed.get(team.id, 0)
            )
            for rank, team in enumerate(teams, start=1)
        ]
    )


def business_leaderboard(session: Session) -> BusinessLeaderboard:
    rows = session.exec(
        select(Task.business_id, func.avg(Task.score), func.count(Task.id))
        .where(Task.status == "published")
        .group_by(Task.business_id)
    ).all()
    stats = sorted(rows, key=lambda row: (-row[1], -row[2], row[0]))
    items = []
    for rank, (business_id, avg_score, count) in enumerate(stats, start=1):
        business = session.get(Business, business_id)
        items.append(
            BusinessRank(
                rank=rank,
                business=BusinessOut.model_validate(business),
                avg_score=round(float(avg_score), 1),
                published_tasks=count,
            )
        )
    return BusinessLeaderboard(items=items)
