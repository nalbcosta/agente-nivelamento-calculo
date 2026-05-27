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
    llm_source: str = "fallback"


class ConsolidacaoResponse(BaseModel):
    consolidation_questions: list[str] = Field(default_factory=list)
    dominated_objectives: list[str] = Field(default_factory=list)
    partial_objectives: list[str] = Field(default_factory=list)
    not_understood_objectives: list[str] = Field(default_factory=list)
    review_recommendation: str
    retrieved_context: list[str] = Field(default_factory=list)
    llm_source: str = "fallback"


class FlashcardItem(BaseModel):
    concept: str
    front: str
    back: str


class FlashcardResponse(BaseModel):
    flashcards: list[FlashcardItem] = Field(default_factory=list)
    memorized_concepts: list[str] = Field(default_factory=list)
    remaining_concepts: list[str] = Field(default_factory=list)
    retrieved_context: list[str] = Field(default_factory=list)
    llm_source: str = "fallback"


class DiagnosticoObjective(BaseModel):
    objective: str
    status: str
    justification: str


class DiagnosticoResponse(BaseModel):
    summary: str
    objectives: list[DiagnosticoObjective] = Field(default_factory=list)
    review_actions: list[str] = Field(default_factory=list)
    retrieved_context: list[str] = Field(default_factory=list)
    llm_source: str = "fallback"