from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import StudentMemorizedConcept
from app.schemas.request import FlashcardRequest
from app.schemas.response import FlashcardItem, FlashcardResponse
from app.services.ingestion import extrair_topicos, normalizar_texto, processar_documento
from app.services.nivelamento_service import garantir_base_vetorial, recuperar_contexto_semantico


def avaliar_flashcards(payload: FlashcardRequest, db: Session) -> FlashcardResponse:
	garantir_base_vetorial(db)
	context_chunks = recuperar_contexto_semantico(payload, db)
	context_text = "\n\n".join(context_chunks)

	objectives = extrair_topicos(context_text)
	if not objectives:
		doc_result = processar_documento(settings.lesson_markdown_path)
		if isinstance(doc_result, dict):
			objectives = doc_result.get("topics", [])

	persisted = _listar_conceitos_memorizados(payload.student_id, db)
	_memorizar_conceitos(payload.student_id, payload.memorized_concepts, db)
	persisted_after = _listar_conceitos_memorizados(payload.student_id, db)
	memorized_set = set(persisted_after.keys())
	known_set = {normalizar_texto(topic.strip()) for topic in payload.known_topics}
	background = normalizar_texto(payload.student_background or "")

	pending: list[str] = []
	for concept in objectives:
		normalized = normalizar_texto(concept)
		if normalized in memorized_set:
			continue
		pending.append(concept)

	if not pending:
		pending = [
			concept
			for concept in objectives
			if normalizar_texto(concept) not in memorized_set
		]

	selected = pending[: payload.target_flashcards]
	flashcards: list[FlashcardItem] = []
	for concept in selected:
		normalized = normalizar_texto(concept)
		flashcards.append(
			FlashcardItem(
				concept=concept,
				front=_build_front(concept),
				back=_build_back(
					concept=concept,
					normalized_concept=normalized,
					known_set=known_set,
					background_text=background,
				),
			)
		)

	remaining = pending[payload.target_flashcards :]

	return FlashcardResponse(
		flashcards=flashcards,
		memorized_concepts=sorted(set(persisted.values()) | set(payload.memorized_concepts) | set(persisted_after.values())),
		remaining_concepts=remaining,
		retrieved_context=context_chunks,
		llm_source="fallback",
	)


def _listar_conceitos_memorizados(student_id: str, db: Session) -> dict[str, str]:
	stmt = select(StudentMemorizedConcept).where(StudentMemorizedConcept.student_id == student_id)
	rows = db.execute(stmt).scalars().all()
	result: dict[str, str] = {}
	for row in rows:
		result[row.normalized_concept] = row.concept
	return result


def _memorizar_conceitos(student_id: str, concepts: list[str], db: Session) -> None:
	if not concepts:
		return

	existing = _listar_conceitos_memorizados(student_id, db)
	created = False
	for concept in concepts:
		if not isinstance(concept, str) or not concept.strip():
			continue
		normalized = normalizar_texto(concept.strip())
		if normalized in existing:
			continue
		db.add(
			StudentMemorizedConcept(
				student_id=student_id,
				concept=concept.strip(),
				normalized_concept=normalized,
			)
		)
		created = True

	if created:
		db.commit()


def _build_front(concept: str) -> str:
	return f"Defina, com suas palavras, o conceito de {concept}."


def _build_back(
	concept: str,
	normalized_concept: str,
	known_set: set[str],
	background_text: str,
) -> str:
	templates = {
		"limites": (
			"Limite descreve o valor que a funcao se aproxima quando x tende a um ponto. "
			"Dica: teste aproximacoes laterais e compare os resultados."
		),
		"derivada": (
			"Derivada e a taxa de variacao instantanea de uma funcao. "
			"Dica: interprete como inclinacao da reta tangente no ponto."
		),
		"regra da cadeia": (
			"A Regra da Cadeia deriva composicoes: derivada da externa na interna vezes derivada da interna. "
			"Dica: identifique primeiro quem e funcao interna."
		),
		"regra de l'hopital": (
			"A Regra de L'Hopital vale para formas indeterminadas como 0/0 ou inf/inf. "
			"Dica: confira continuidade e derive numerador e denominador separadamente."
		),
	}

	if normalized_concept in templates:
		return templates[normalized_concept]

	if normalized_concept in known_set or normalized_concept in background_text:
		return (
			f"{concept} aparece como ponto ja conhecido por voce. "
			"Dica: explique o conceito em 1 frase e resolva 1 exemplo simples."
		)

	return (
		f"{concept} e um conceito central de Calculo I para modelar variacao e comportamento de funcoes. "
		"Dica: relacione definicao formal com um exemplo numerico curto."
	)
