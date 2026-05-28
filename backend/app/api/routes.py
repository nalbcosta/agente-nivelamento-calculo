from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Student, StudentMemorizedConcept
from app.db.session import get_db
from app.schemas.request import (
	ConsolidacaoRequest,
	DiagnosticoRequest,
	FlashcardRequest,
	NivelamentoRequest,
)
from app.schemas.response import (
	ConsolidacaoResponse,
	DiagnosticoResponse,
	FlashcardResponse,
	HealthResponse,
	NivelamentoResponse,
	StudentProfileResponse,
)
from app.services.consolidacao_service import avaliar_consolidacao
from app.services.diagnostico_service import avaliar_diagnostico
from app.services.flashcard_service import avaliar_flashcards
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


@router.post("/consolidacao", response_model=ConsolidacaoResponse)
def consolidacao(
	payload: ConsolidacaoRequest,
	db: Session = Depends(get_db),
) -> ConsolidacaoResponse:
	return avaliar_consolidacao(payload, db)


@router.post("/diagnostico", response_model=DiagnosticoResponse)
def diagnostico(
	payload: DiagnosticoRequest,
	db: Session = Depends(get_db),
) -> DiagnosticoResponse:
	return avaliar_diagnostico(payload, db)


@router.post("/flashcards", response_model=FlashcardResponse)
def flashcards(
	payload: FlashcardRequest,
	db: Session = Depends(get_db),
) -> FlashcardResponse:
	return avaliar_flashcards(payload, db)


@router.post("/nivelamento/ingest")
def ingest_lesson(db: Session = Depends(get_db)) -> dict[str, object]:
	source = settings.lesson_markdown_path.split("/")[-1]
	return ingerir_documento_no_pgvector(db, settings.lesson_markdown_path, source)


@router.get("/students/{student_id}", response_model=StudentProfileResponse)
def get_student_profile(student_id: str, db: Session = Depends(get_db)) -> StudentProfileResponse:
	import json

	student = db.execute(select(Student).where(Student.student_id == student_id)).scalar_one_or_none()

	memorized_rows = db.execute(
		select(StudentMemorizedConcept).where(StudentMemorizedConcept.student_id == student_id)
	).scalars().all()
	memorized = [row.concept for row in memorized_rows]

	if student is None:
		return StudentProfileResponse(
			student_id=student_id,
			memorized_concepts=memorized,
		)

	known_topics: list[str] = []
	if student.known_topics_json:
		try:
			parsed = json.loads(student.known_topics_json)
			if isinstance(parsed, list):
				known_topics = [str(t) for t in parsed]
		except Exception:
			pass

	previous_questions: list[str] = []
	if student.consolidation_history_json:
		try:
			parsed = json.loads(student.consolidation_history_json)
			if isinstance(parsed, list):
				previous_questions = [str(q) for q in parsed]
		except Exception:
			pass

	return StudentProfileResponse(
		student_id=student.student_id,
		background=student.background,
		known_topics=known_topics,
		memorized_concepts=memorized,
		previous_consolidation_questions=previous_questions,
	)
