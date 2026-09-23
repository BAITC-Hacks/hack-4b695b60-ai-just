"""AI transparency and runtime provider control."""

import json
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.ai.service import active_provider, prompt_info, provider_chain, provider_mode, set_provider_mode
from app.ai.trace import list_traces
from app.db import get_session
from app.errors import not_found
from app.models import AITrace

router = APIRouter(prefix="/api/ai", tags=["ai"])
SessionDep = Annotated[Session, Depends(get_session)]


class ProviderModeIn(BaseModel):
    mode: Literal["auto", "openai", "brev", "stub"]


@router.get("/traces", response_model=list[AITrace])
def traces(
    session: SessionDep, task_id: int | None = None, limit: int = Query(20, ge=1, le=100)
) -> list[AITrace]:
    return list_traces(session, task_id, limit)


@router.get("/prompts")
def prompts() -> list[dict[str, Any]]:
    return prompt_info()


@router.get("/provider")
def get_provider() -> dict[str, Any]:
    return {
        "mode": provider_mode(),
        "chain": [item.model_dump() for item in provider_chain()],
        "active": active_provider(),
    }


@router.put("/provider")
def put_provider(payload: ProviderModeIn) -> dict[str, Any]:
    set_provider_mode(payload.mode)
    return get_provider()


@router.get("/eval/latest")
def latest_eval() -> list[dict[str, Any]]:
    report_dir = Path(__file__).resolve().parents[2] / "eval" / "reports"
    reports = sorted(report_dir.glob("*.json"))
    if not reports:
        raise not_found("EVAL_NOT_FOUND", "Отчёт оценки AI ещё не создан")
    return json.loads(reports[-1].read_text(encoding="utf-8"))
