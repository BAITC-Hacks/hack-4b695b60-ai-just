from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.db import get_session
from app.errors import not_found
from app.models import Business, Team
from app.schemas import BusinessCreate, BusinessOut, TeamOut

router = APIRouter(prefix="/api", tags=["participants"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/businesses", response_model=list[BusinessOut])
def list_businesses(session: SessionDep) -> list[Business]:
    return list(session.exec(select(Business).order_by(Business.id)).all())


@router.post("/businesses", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
def create_business(payload: BusinessCreate, session: SessionDep) -> Business:
    business = Business(name=payload.name.strip(), industry=payload.industry)
    session.add(business)
    session.commit()
    session.refresh(business)
    return business


@router.get("/teams", response_model=list[TeamOut])
def list_teams(session: SessionDep) -> list[Team]:
    return list(session.exec(select(Team).order_by(Team.id)).all())


@router.get("/teams/{team_id}", response_model=TeamOut)
def get_team(team_id: int, session: SessionDep) -> Team:
    team = session.get(Team, team_id)
    if team is None:
        raise not_found("TEAM_NOT_FOUND", "Команда не найдена")
    return team
