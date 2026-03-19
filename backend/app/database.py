"""Database connection and session management."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """Yield a database session, ensuring cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def execute_query(query: str, params: dict | None = None) -> list[dict]:
    """Execute a raw SQL query and return results as list of dicts.

    This is the core data retrieval function that all tools use.
    We use raw SQL for clarity and because the queries are
    read-only aggregations — no ORM overhead needed.
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]
