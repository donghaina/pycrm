import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://pycrm:pycrm@localhost:5432/pycrm")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass


def init_db():
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS crm"))
        conn.execute(text("ALTER TABLE IF EXISTS crm.processed_events ADD COLUMN IF NOT EXISTS error_type TEXT"))
        conn.execute(text("ALTER TABLE IF EXISTS crm.processed_events ADD COLUMN IF NOT EXISTS error_stage TEXT"))
        conn.execute(text("ALTER TABLE IF EXISTS crm.processed_events ADD COLUMN IF NOT EXISTS attempt_count INT DEFAULT 0"))
    Base.metadata.create_all(bind=engine)
