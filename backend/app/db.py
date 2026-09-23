from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401
from app.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {},
)


def create_tables() -> None:
    SQLModel.metadata.create_all(engine)


def drop_tables() -> None:
    SQLModel.metadata.drop_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
