from pydantic import BaseModel, Field


class NivelamentoRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=120)
    student_background: str | None = Field(default=None, max_length=3000)
    known_topics: list[str] = Field(default_factory=list)
    top_k: int | None = Field(default=None, ge=1, le=10)