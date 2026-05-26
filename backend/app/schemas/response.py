from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class NivelamentoResponse(BaseModel):
    is_ready: bool
    missing_prerequisites: list[str] = Field(default_factory=list)
    support_text: str