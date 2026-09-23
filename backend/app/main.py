import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import admin, ai, catalog, leaderboard, meta, participants, proposals, recommendations, tasks
from app.config import get_settings
from app.db import create_tables
from app.seed import ensure_seeded

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if get_settings().seed_on_startup:
        ensure_seeded()
    else:
        create_tables()
    yield


app = FastAPI(title="AI Sana Challenge Hub API", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (meta, participants, tasks, catalog, proposals, leaderboard, ai, recommendations, admin):
    app.include_router(module.router)
