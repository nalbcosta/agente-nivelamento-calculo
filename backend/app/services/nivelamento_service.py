from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import DocumentChunk, StudentReadiness
from app.prompts.nivelamento_prompt import construir_prompt_nivelamento
from app.schemas.request import NivelamentoRequest
from app.schemas.response import NivelamentoResponse
from app.services.embedding_service import gerar_embedding
from app.services.ingestion import (
	ingerir_documento_no_pgvector,
	normalizar_texto,
	processar_documento,
	extrair_prerequisitos,
	extrair_topicos,
)
from app.services.llm_service import gerar_texto_nivelamento_llm


def avaliar_nivelamento(payload: NivelamentoRequest, db: Session) -> NivelamentoResponse:
	garantir_base_vetorial(db)
	context_chunks = recuperar_contexto_semantico(payload, db)
	context_text = "\n\n".join(context_chunks)

	prerequisites = extrair_prerequisitos(context_text)
	topics = extrair_topicos(context_text)
	if not prerequisites or not topics:
		doc_result = processar_documento(settings.lesson_markdown_path)
		if isinstance(doc_result, dict):
			if not prerequisites:
				prerequisites = doc_result.get("prerequisites", [])
			if not topics:
				topics = doc_result.get("topics", [])

	normalized_known = {normalizar_texto(topic.strip()) for topic in payload.known_topics}
	background = normalizar_texto(payload.student_background or "")

	missing = []
	for prerequisite in prerequisites:
		lowered = normalizar_texto(prerequisite)
		if lowered not in normalized_known and lowered not in background:
			missing.append(prerequisite)

	is_ready = len(missing) == 0
	fallback_text = gerar_texto_nivelamento(is_ready, missing, topics)
	prompt = construir_prompt_nivelamento(
		student_background=payload.student_background or "",
		known_topics=payload.known_topics,
		extracted_prerequisites=prerequisites,
		missing_prerequisites=missing,
		retrieved_context=context_chunks,
	)
	support_text = gerar_texto_nivelamento_llm(prompt=prompt, fallback_text=fallback_text)

	readiness = StudentReadiness(
		student_id=payload.student_id,
		is_ready=is_ready,
		gaps_summary=", ".join(missing) if missing else None,
		support_text=support_text,
	)
	db.add(readiness)
	db.commit()

	return NivelamentoResponse(
		is_ready=is_ready,
		extracted_prerequisites=prerequisites,
		missing_prerequisites=missing,
		detected_lesson_topics=topics,
		retrieved_context=context_chunks,
		support_text=support_text,
	)


def garantir_base_vetorial(db: Session) -> None:
	source = settings.lesson_markdown_path.split("/")[-1]
	count_stmt = select(DocumentChunk.id).where(DocumentChunk.source == source).limit(1)
	existing = db.execute(count_stmt).scalar_one_or_none()
	if existing is None:
		ingerir_documento_no_pgvector(db, settings.lesson_markdown_path, source)


def recuperar_contexto_semantico(payload: NivelamentoRequest, db: Session) -> list[str]:
	source = settings.lesson_markdown_path.split("/")[-1]
	top_k = payload.top_k or settings.rag_top_k_default
	query_text = " ".join(payload.known_topics)
	if payload.student_background:
		query_text = f"{query_text} {payload.student_background}".strip()
	if not query_text:
		query_text = "pre requisitos para calculo I"

	query_embedding = gerar_embedding(query_text)

	stmt = (
		select(DocumentChunk)
		.where(DocumentChunk.source == source)
		.where(DocumentChunk.embedding.is_not(None))
		.order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
		.limit(top_k)
	)
	rows = db.execute(stmt).scalars().all()
	if not rows:
		return []
	return [row.chunk_text for row in rows]


def gerar_texto_nivelamento(is_ready: bool, missing: list[str], topics: list[str]) -> str:
	if is_ready:
		focus = ", ".join(topics[:2]) if topics else "limites e derivadas"
		return (
			"Diagnostico: apto para iniciar Calculo I. "
			f"Recomendacao: comecar por {focus} e resolver 2 exercicios guiados."
		)

	missing_text = ", ".join(missing)
	return (
		"Diagnostico: ainda nao apto para o melhor aproveitamento da aula. "
		f"Nivelamento sugerido: revisar {missing_text} com resumo teorico curto e 3 exercicios basicos antes de avancar."
	)
