import os
import time
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.modules.users.infrastructure.models import Base


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./identity.db")

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(retries: int = 10, delay_seconds: int = 2) -> None:
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            _ensure_user_schema()
            return
        except Exception:
            if attempt == retries:
                raise
            time.sleep(delay_seconds)


def _ensure_user_schema() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("identity_users"):
        return
    column_names = {column["name"] for column in inspector.get_columns("identity_users")}
    if "phone_number" in column_names:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE identity_users ADD COLUMN phone_number VARCHAR(40)"))


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
