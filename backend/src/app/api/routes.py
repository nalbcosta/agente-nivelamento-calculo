from fastapi import APIRouter

from backend.app.schemas.request import NivelamentoRequest
from backend.app.schemas.response import HealthResponse, NivelamentoResponse
from backend.app.services.nivelamento_service import avaliar_nivelamento

router = APIRouter(tags=["api"])


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
	return HealthResponse(status="ok")


@router.post("/nivelamento", response_model=NivelamentoResponse)
def nivelamento(payload: NivelamentoRequest) -> NivelamentoResponse:
	return avaliar_nivelamento(payload)
