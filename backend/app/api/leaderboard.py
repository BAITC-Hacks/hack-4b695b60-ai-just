from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.schemas import BusinessLeaderboard, TeamLeaderboard
from app.services.proposal_service import business_leaderboard, team_leaderboard

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/teams", response_model=TeamLeaderboard)
def teams(session: SessionDep) -> TeamLeaderboard:
    return team_leaderboard(session)


@router.get("/businesses", response_model=BusinessLeaderboard)
def businesses(session: SessionDep) -> BusinessLeaderboard:
    return business_leaderboard(session)
