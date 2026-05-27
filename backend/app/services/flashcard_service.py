import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import StudentMemorizedConcept
from app.prompts.flashcard_prompt import (
	FLASHCARD_SYSTEM_PROMPT,
	construir_prompt_flashcards,
)
from app.schemas.request import FlashcardRequest
from app.schemas.response import FlashcardItem, FlashcardResponse
from app.services.ingestion import extrair_topicos, normalizar_texto, processar_documento
from app.services.llm_service import gerar_texto_llm
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
	llm_items, llm_source = _gerar_flashcards_llm(payload, context_chunks, selected)
	flashcards: list[FlashcardItem] = []
	for concept in selected:
		normalized = normalizar_texto(concept)
		llm_item = llm_items.get(normalized)
		if llm_item:
			flashcards.append(llm_item)
			continue
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
		llm_source=llm_source if llm_items else "fallback",
	)


def _gerar_flashcards_llm(
	payload: FlashcardRequest,
	retrieved_context: list[str],
	selected_concepts: list[str],
) -> tuple[dict[str, FlashcardItem], str]:
	if not selected_concepts:
		return {}, "fallback"
	prompt = construir_prompt_flashcards(
		student_background=payload.student_background or "",
		known_topics=payload.known_topics,
		retrieved_context=retrieved_context,
		pending_concepts=selected_concepts,
	)
	fallback_json = '{"flashcards": []}'
	raw_text, source = gerar_texto_llm(
		prompt=prompt,
		fallback_text=fallback_json,
		system_prompt=FLASHCARD_SYSTEM_PROMPT,
	)
	selected_norm_map = {normalizar_texto(concept): concept for concept in selected_concepts}
	result: dict[str, FlashcardItem] = {}

	parsed = _parse_flashcards_json(raw_text)
	if parsed:
		items = parsed.get("flashcards")
		if isinstance(items, list):
			result = _build_flashcards_from_json_items(items, selected_norm_map)

	if not result:
		result = _parse_flashcards_text_blocks(raw_text, selected_concepts)

	if not result and source != "fallback":
		for concept in selected_concepts:
			single = _build_single_flashcard_from_plain_text(raw_text, concept)
			if single:
				result.update(single)

	if not result:
		return {}, "fallback"
	return result, source


def _build_single_flashcard_from_plain_text(raw_text: str, concept: str) -> dict[str, FlashcardItem]:
	text = raw_text.strip()
	if not text:
		return {}

	if "```" in text:
		text = text.replace("```json", "").replace("```", "").strip()

	if text == '{"flashcards": []}':
		return {}

	lines = [line.strip(" -\t") for line in text.splitlines() if line.strip()]
	if not lines:
		return {}

	front = ""
	for line in lines:
		if line.endswith("?"):
			front = line
			break
	if not front:
		front = _build_front(concept)

	back_source = " ".join(lines)
	if front in back_source:
		back_source = back_source.replace(front, "", 1).strip(" :-")
	back = back_source or f"{concept} e um conceito importante em Calculo I."

	# Keep answer concise to stay compatible with response contracts and UI.
	if len(back) > 280:
		back = back[:277].rstrip() + "..."

	normalized = normalizar_texto(concept)
	return {
		normalized: FlashcardItem(
			concept=concept,
			front=front,
			back=back,
		)
	}


def _build_flashcards_from_json_items(
	items: list[object],
	selected_norm_map: dict[str, str],
) -> dict[str, FlashcardItem]:
	result: dict[str, FlashcardItem] = {}
	for entry in items:
		if not isinstance(entry, dict):
			continue
		concept = entry.get("concept")
		front = entry.get("front")
		back = entry.get("back")
		if not all(isinstance(field, str) and field.strip() for field in [concept, front, back]):
			continue
		resolved = _resolve_selected_concept(concept.strip(), selected_norm_map)
		if not resolved:
			continue
		resolved_norm = normalizar_texto(resolved)
		if resolved_norm in result:
			continue
		result[resolved_norm] = FlashcardItem(
			concept=resolved,
			front=front.strip(),
			back=back.strip(),
		)
	return result


def _resolve_selected_concept(raw_concept: str, selected_norm_map: dict[str, str]) -> str | None:
	normalized = normalizar_texto(raw_concept)
	if normalized in selected_norm_map:
		return selected_norm_map[normalized]

	for selected_norm, selected_raw in selected_norm_map.items():
		if selected_norm in normalized or normalized in selected_norm:
			return selected_raw
	return None


def _parse_flashcards_json(raw_text: str) -> dict[str, object] | None:
	if not raw_text.strip():
		return None

	candidate = raw_text.strip()
	if "```" in candidate:
		candidate = candidate.replace("```json", "").replace("```", "").strip()

	try:
		parsed = json.loads(candidate)
		if isinstance(parsed, list):
			return {"flashcards": parsed}
		if isinstance(parsed, dict):
			if "flashcards" in parsed:
				return parsed
			for alias in ["cards", "items", "flash_cards"]:
				value = parsed.get(alias)
				if isinstance(value, list):
					return {"flashcards": value}
			return parsed
	except Exception:
		pass

	start = candidate.find("{")
	end = candidate.rfind("}")
	if start == -1 or end == -1 or end <= start:
		return None

	try:
		parsed = json.loads(candidate[start : end + 1])
		if isinstance(parsed, list):
			return {"flashcards": parsed}
		if isinstance(parsed, dict):
			if "flashcards" in parsed:
				return parsed
			for alias in ["cards", "items", "flash_cards"]:
				value = parsed.get(alias)
				if isinstance(value, list):
					return {"flashcards": value}
			return parsed
	except Exception:
		return None

	return None


def _parse_flashcards_text_blocks(raw_text: str, selected_concepts: list[str]) -> dict[str, FlashcardItem]:
	text = raw_text.strip()
	if not text:
		return {}

	pattern = re.compile(
		r"Frente\s*:\s*(?P<front>.+?)\s*Verso\s*:\s*(?P<back>.+?)(?=\n\s*Frente\s*:|$)",
		re.IGNORECASE | re.DOTALL,
	)
	matches = list(pattern.finditer(text))
	if not matches:
		return {}

	result: dict[str, FlashcardItem] = {}
	for idx, match in enumerate(matches):
		if idx >= len(selected_concepts):
			break
		concept = selected_concepts[idx]
		normalized = normalizar_texto(concept)
		front = match.group("front").strip(" -\n\t")
		back = match.group("back").strip(" -\n\t")
		if not front or not back:
			continue
		if normalized in result:
			continue
		result[normalized] = FlashcardItem(
			concept=concept,
			front=front,
			back=back,
		)
	return result


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
