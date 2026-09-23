from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.db import get_session
from app.schemas import (
    BusinessAction,
    DecisionIn,
    MilestoneConfirmOut,
    MilestoneCreate,
    MilestoneOut,
    ProposalCreate,
    ProposalOut,
    TeamOut,
)
from app.services import proposal_service as svc
from app.services.task_views import get_task_or_404

router = APIRouter(prefix="/api", tags=["proposals"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/tasks/{task_id}/proposals", response_model=ProposalOut, status_code=status.HTTP_201_CREATED)
def create_proposal(task_id: int, payload: ProposalCreate, session: SessionDep) -> ProposalOut:
    task = get_task_or_404(session, task_id)
    team = svc.get_team_or_404(session, payload.team_id)
    proposal = svc.create_proposal(
        session,
        task,
        team,
        idea=payload.idea,
        plan=payload.plan,
        timeline=payload.timeline,
        prototype_url=str(payload.prototype_url) if payload.prototype_url else None,
    )
    session.commit()
    session.refresh(proposal)
    return svc.proposal_out(session, proposal)


@router.get("/tasks/{task_id}/proposals", response_model=list[ProposalOut])
def list_task_proposals(
    task_id: int, business_id: Annotated[int, Query()], session: SessionDep
) -> list[ProposalOut]:
    task = get_task_or_404(session, task_id)
    svc.ensure_owner(task, business_id)
    return [svc.proposal_out(session, proposal) for proposal in svc.proposals_for_task(session, task.id)]


@router.get("/teams/{team_id}/proposals", response_model=list[ProposalOut])
def list_team_proposals(team_id: int, session: SessionDep) -> list[ProposalOut]:
    team = svc.get_team_or_404(session, team_id)
    return [svc.proposal_out(session, proposal) for proposal in svc.proposals_for_team(session, team.id)]


@router.post("/proposals/{proposal_id}/decision", response_model=ProposalOut)
def decide(proposal_id: int, payload: DecisionIn, session: SessionDep) -> ProposalOut:
    proposal = svc.get_proposal_or_404(session, proposal_id)
    svc.ensure_owner(get_task_or_404(session, proposal.task_id), payload.business_id)
    svc.decide(proposal, payload.decision, payload.comment)
    session.add(proposal)
    session.commit()
    session.refresh(proposal)
    return svc.proposal_out(session, proposal)


@router.post(
    "/proposals/{proposal_id}/milestones", response_model=MilestoneOut, status_code=status.HTTP_201_CREATED
)
def create_milestone(proposal_id: int, payload: MilestoneCreate, session: SessionDep) -> MilestoneOut:
    proposal = svc.get_proposal_or_404(session, proposal_id)
    svc.ensure_owner(get_task_or_404(session, proposal.task_id), payload.business_id)
    milestone = svc.add_milestone(session, proposal, payload.title, payload.points)
    session.commit()
    session.refresh(milestone)
    return MilestoneOut.model_validate(milestone)


@router.post("/milestones/{milestone_id}/confirm", response_model=MilestoneConfirmOut)
def confirm_milestone(milestone_id: int, payload: BusinessAction, session: SessionDep) -> MilestoneConfirmOut:
    milestone = svc.get_milestone_or_404(session, milestone_id)
    proposal = svc.get_proposal_or_404(session, milestone.proposal_id)
    svc.ensure_owner(get_task_or_404(session, proposal.task_id), payload.business_id)
    team = svc.confirm_milestone(session, milestone, proposal)
    session.commit()
    session.refresh(milestone)
    session.refresh(team)
    return MilestoneConfirmOut(
        milestone=MilestoneOut.model_validate(milestone), team=TeamOut.model_validate(team)
    )
