from sqlalchemy import text

from app.db import models  # noqa: F401
from app.db.session import Base, engine


def init_db() -> None:
	with engine.begin() as connection:
		connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
	Base.metadata.create_all(bind=engine)
