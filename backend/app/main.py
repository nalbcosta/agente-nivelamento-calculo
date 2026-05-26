from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import router as api_router
from app.core.config import settings
from app.db.init_db import init_db


def create_app() -> FastAPI:
	app = FastAPI(title=settings.app_name, version=settings.app_version)
	app.include_router(api_router, prefix=settings.api_v1_prefix)
	try:
		init_db()
	except SQLAlchemyError:
		# O backend continua subindo e o banco pode ser inicializado depois.
		pass

	@app.get("/", tags=["system"])
	def root() -> dict[str, str]:
		return {"message": "API de nivelamento em execucao"}

	return app


app = create_app()