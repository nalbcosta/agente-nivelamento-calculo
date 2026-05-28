from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.config import settings
from app.prompts.diagnostico_prompt import DIAGNOSTICO_SYSTEM_PROMPT, construir_prompt_diagnostico
from app.schemas.request import DiagnosticoRequest
from app.schemas.response import DiagnosticoObjective, DiagnosticoResponse
from app.services.ingestion import extrair_topicos, normalizar_texto, processar_documento
from app.services.llm_service import gerar_texto_llm
from app.services.nivelamento_service import garantir_base_vetorial, recuperar_contexto_semantico


def avaliar_diagnostico(payload: DiagnosticoRequest, db: Session) -> DiagnosticoResponse:
	garantir_base_vetorial(db)
	context_chunks = recuperar_contexto_semantico(payload, db)
	context_text = "\n\n".join(context_chunks)

	objectives = extrair_topicos(context_text)
	if not objectives:
		doc_result = processar_documento(settings.lesson_markdown_path)
		if isinstance(doc_result, dict):
			objectives = doc_result.get("topics", [])

	fallback = _fallback_diagnostico(payload, objectives)
	prompt = construir_prompt_diagnostico(
		student_background=payload.student_background or "",
		known_topics=payload.known_topics,
		answered_questions=payload.answered_questions,
		objectives=objectives,
		dominated_initial=[item.objective for item in fallback["objectives"] if item.status == "Dominado"],
		partial_initial=[item.objective for item in fallback["objectives"] if item.status == "Parcial"],
		not_understood_initial=[item.objective for item in fallback["objectives"] if item.status == "Nao dominado"],
		retrieved_context=context_chunks,
	)

	llm_text, llm_source = gerar_texto_llm(
		prompt=prompt,
		fallback_text=json.dumps(_fallback_as_dict(fallback), ensure_ascii=False),
		system_prompt=DIAGNOSTICO_SYSTEM_PROMPT,
	)
	parsed = _parse_diagnostico_json(llm_text)
	if not parsed:
		return DiagnosticoResponse(
			summary=fallback["summary"],
			objectives=fallback["objectives"],
			review_actions=fallback["review_actions"],
			retrieved_context=context_chunks,
			llm_source="fallback",
		)

	objectives_payload = []
	for item in parsed.get("objectives", []):
		if not isinstance(item, dict):
			continue
		objective = item.get("objective")
		status = item.get("status")
		justification = item.get("justification")
		if not all(isinstance(field, str) and field.strip() for field in [objective, status, justification]):
			continue
		objectives_payload.append(
			DiagnosticoObjective(
				objective=objective.strip(),
				status=status.strip(),
				justification=justification.strip(),
			)
		)

	if not objectives_payload:
		objectives_payload = fallback["objectives"]
		llm_source = "fallback"

	review_actions = [item for item in parsed.get("review_actions", []) if isinstance(item, str) and item.strip()]
	if not review_actions:
		review_actions = fallback["review_actions"]
		llm_source = "fallback"

	summary = parsed.get("summary")
	if not isinstance(summary, str) or not summary.strip():
		summary = fallback["summary"]
		llm_source = "fallback"

	return DiagnosticoResponse(
		summary=summary,
		objectives=objectives_payload,
		review_actions=review_actions,
		retrieved_context=context_chunks,
		llm_source=llm_source,
	)


def _fallback_diagnostico(payload: DiagnosticoRequest, objectives: list[str]) -> dict[str, object]:
	normalized_known = {normalizar_texto(topic.strip()) for topic in payload.known_topics}
	answers_text = normalizar_texto(" ".join(payload.answered_questions))
	background = normalizar_texto(payload.student_background or "")

	items: list[DiagnosticoObjective] = []
	for objective in objectives:
		normalized = normalizar_texto(objective)
		if normalized in normalized_known:
			items.append(
				DiagnosticoObjective(
					objective=objective,
					status="Dominado",
					justification="O objetivo aparece como topico conhecido informado pelo aluno.",
				)
			)
		elif normalized in answers_text or normalized in background:
			items.append(
				DiagnosticoObjective(
					objective=objective,
					status="Parcial",
					justification="Ha evidencia parcial nas respostas e no contexto apresentado pelo aluno.",
				)
			)
		else:
			items.append(
				DiagnosticoObjective(
					objective=objective,
					status="Nao dominado",
					justification="Nao foram encontradas evidencias suficientes de dominio nas respostas fornecidas.",
				)
			)

	if not items:
		items = [
			DiagnosticoObjective(
				objective="Topicos da aula",
				status="Parcial",
				justification="Contexto insuficiente para classificar todos os objetivos com precisao.",
			)
		]

	not_mastered = [item.objective for item in items if item.status != "Dominado"]
	focus = ", ".join(not_mastered[:2]) if not_mastered else "proximo modulo"

	return {
		"summary": f"Diagnostico consolidado da aula realizado. Priorize revisao em {focus}.",
		"objectives": items,
		"review_actions": [
			"Revisar definicoes dos objetivos nao dominados com exemplos curtos.",
			"Resolver 3 exercicios focados nos pontos parciais e nao dominados.",
			"Registrar os conceitos dominados para orientar os proximos flashcards.",
		],
	}


def _fallback_as_dict(payload: dict[str, object]) -> dict[str, object]:
	return {
		"summary": payload["summary"],
		"objectives": [
			{
				"objective": item.objective,
				"status": item.status,
				"justification": item.justification,
			}
			for item in payload["objectives"]
		],
		"review_actions": payload["review_actions"],
	}


def _parse_diagnostico_json(raw_text: str) -> dict[str, object] | None:
	if not raw_text.strip():
		return None

	candidate = raw_text.strip()
	if "```" in candidate:
		candidate = candidate.replace("```json", "").replace("```", "").strip()

	try:
		parsed = json.loads(candidate)
		if isinstance(parsed, dict):
			return parsed
	except Exception:
		pass

	start = candidate.find("{")
	end = candidate.rfind("}")
	if start == -1 or end == -1 or end <= start:
		return None

	try:
		parsed = json.loads(candidate[start : end + 1])
		if isinstance(parsed, dict):
			return parsed
	except Exception:
		return None

	return None
