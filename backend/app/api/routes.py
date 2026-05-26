from fastapi import APIRouter

from app.schemas.request import NivelamentoRequest
from app.schemas.response import HealthResponse, NivelamentoResponse
from app.services.nivelamento_service import avaliar_nivelamento

router = APIRouter(tags=["api"])


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
	return HealthResponse(status="ok")


@router.post("/nivelamento", response_model=NivelamentoResponse)
def nivelamento(payload: NivelamentoRequest) -> NivelamentoResponse:
	return avaliar_nivelamento(payload)
