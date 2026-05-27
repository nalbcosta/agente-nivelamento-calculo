from pydantic import BaseModel, Field


class NivelamentoRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=120)
    student_background: str | None = Field(default=None, max_length=3000)
    known_topics: list[str] = Field(default_factory=list)
    top_k: int | None = Field(default=None, ge=1, le=10)


class ConsolidacaoRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=120)
    student_background: str | None = Field(default=None, max_length=3000)
    known_topics: list[str] = Field(default_factory=list)
    answered_questions: list[str] = Field(default_factory=list, max_length=20)
    top_k: int | None = Field(default=None, ge=1, le=10)


class FlashcardRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=120)
    student_background: str | None = Field(default=None, max_length=3000)
    known_topics: list[str] = Field(default_factory=list)
    memorized_concepts: list[str] = Field(default_factory=list, max_length=50)
    top_k: int | None = Field(default=None, ge=1, le=10)
    target_flashcards: int = Field(default=5, ge=1, le=8)


class DiagnosticoRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=120)
    student_background: str | None = Field(default=None, max_length=3000)
    known_topics: list[str] = Field(default_factory=list)
    answered_questions: list[str] = Field(default_factory=list, max_length=20)
    top_k: int | None = Field(default=None, ge=1, le=10)