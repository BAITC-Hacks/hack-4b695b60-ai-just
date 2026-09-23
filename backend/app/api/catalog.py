from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db import get_session
from app.domain.fields import LevelKey
from app.schemas import CatalogPage, PublicTask
from app.services.catalog_views import get_published_or_404, list_catalog, public_task

router = APIRouter(prefix="/api", tags=["catalog"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/catalog", response_model=CatalogPage)
def get_catalog(
    session: SessionDep,
    topic: Annotated[str | None, Query()] = None,
    level: Annotated[list[LevelKey] | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    sort: Annotated[Literal["rating", "newest"], Query()] = "rating",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CatalogPage:
    return list_catalog(
        session,
        topic=topic,
        levels=set(level or []),
        query=q.strip() if q else None,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/catalog/{task_id}", response_model=PublicTask)
def get_public_task(task_id: int, session: SessionDep) -> PublicTask:
    return public_task(session, get_published_or_404(session, task_id))
