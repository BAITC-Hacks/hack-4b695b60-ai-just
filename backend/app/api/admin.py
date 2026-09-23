from fastapi import APIRouter

from app.schemas import OkResponse
from app.seed import reset_and_seed

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/reset", response_model=OkResponse)
def reset_demo() -> OkResponse:
    reset_and_seed()
    return OkResponse()
