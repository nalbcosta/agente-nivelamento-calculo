from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class NivelamentoResponse(BaseModel):
    is_ready: bool
    extracted_prerequisites: list[str] = Field(default_factory=list)
    missing_prerequisites: list[str] = Field(default_factory=list)
    detected_lesson_topics: list[str] = Field(default_factory=list)
    retrieved_context: list[str] = Field(default_factory=list)
    support_text: str