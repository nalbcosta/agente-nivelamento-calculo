from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.request import NivelamentoRequest
from app.schemas.response import HealthResponse, NivelamentoResponse
from app.services.ingestion import ingerir_documento_no_pgvector
from app.services.nivelamento_service import avaliar_nivelamento

router = APIRouter(tags=["api"])


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
	return HealthResponse(status="ok")


@router.post("/nivelamento", response_model=NivelamentoResponse)
def nivelamento(
	payload: NivelamentoRequest,
	db: Session = Depends(get_db),
) -> NivelamentoResponse:
	return avaliar_nivelamento(payload, db)


@router.post("/nivelamento/ingest")
def ingest_lesson(db: Session = Depends(get_db)) -> dict[str, object]:
	source = settings.lesson_markdown_path.split("/")[-1]
	return ingerir_documento_no_pgvector(db, settings.lesson_markdown_path, source)
