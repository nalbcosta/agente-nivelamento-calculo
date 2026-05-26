from fastapi import FastAPI

from backend.app.api.routes import router as api_router
from backend.app.core.config import settings


def create_app() -> FastAPI:
	app = FastAPI(title=settings.app_name, version=settings.app_version)
	app.include_router(api_router, prefix=settings.api_v1_prefix)

	@app.get("/", tags=["system"])
	def root() -> dict[str, str]:
		return {"message": "API de nivelamento em execucao"}

	return app


app = create_app()