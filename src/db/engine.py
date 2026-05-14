from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.config import DB_PATH

_engine = None


def get_engine(db_path=None):
    global _engine
    if _engine is None:
        path = db_path or str(DB_PATH)
        _engine = create_engine(f"sqlite:///{path}", echo=False)
    return _engine


def get_session() -> Session:
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def init_db():
    from src.db.models import Base
    Base.metadata.create_all(get_engine())
