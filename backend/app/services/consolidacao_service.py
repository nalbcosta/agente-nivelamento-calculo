import json

from sqlalchemy.orm import Session

from app.core.config import settings
from app.prompts.consolidacao_prompt import (
    CONSOLIDACAO_SYSTEM_PROMPT,
    construir_prompt_consolidacao,
)
from app.schemas.request import ConsolidacaoRequest
from app.schemas.response import ConsolidacaoResponse
from app.services.ingestion import extrair_topicos, normalizar_texto, processar_documento
from app.services.llm_service import gerar_texto_llm
from app.services.nivelamento_service import garantir_base_vetorial, recuperar_contexto_semantico


def avaliar_consolidacao(payload: ConsolidacaoRequest, db: Session) -> ConsolidacaoResponse:
    garantir_base_vetorial(db)
    context_chunks = recuperar_contexto_semantico(payload, db)
    context_text = "\n\n".join(context_chunks)

    objectives = extrair_topicos(context_text)
    if not objectives:
        doc_result = processar_documento(settings.lesson_markdown_path)
        if isinstance(doc_result, dict):
            objectives = doc_result.get("topics", [])

    normalized_known = {normalizar_texto(topic.strip()) for topic in payload.known_topics}
    background = normalizar_texto(payload.student_background or "")

    dominated_initial: list[str] = []
    not_understood_initial: list[str] = []
    for objective in objectives:
        lowered = normalizar_texto(objective)
        if lowered in normalized_known or lowered in background:
            dominated_initial.append(objective)
        else:
            not_understood_initial.append(objective)

    fallback = _fallback_consolidacao(
        objectives=objectives,
        dominated=dominated_initial,
        not_understood=not_understood_initial,
    )

    prompt = construir_prompt_consolidacao(
        student_background=payload.student_background or "",
        known_topics=payload.known_topics,
        answered_questions=payload.answered_questions,
        objectives=objectives,
        dominated_initial=dominated_initial,
        not_understood_initial=not_understood_initial,
        retrieved_context=context_chunks,
    )

    llm_text, llm_source = gerar_texto_llm(
        prompt=prompt,
        fallback_text=json.dumps(fallback, ensure_ascii=False),
        system_prompt=CONSOLIDACAO_SYSTEM_PROMPT,
    )

    parsed = _parse_consolidacao_json(llm_text)
    if not parsed:
        parsed = fallback
        llm_source = "fallback"

    return ConsolidacaoResponse(
        consolidation_questions=parsed.get("consolidation_questions", []),
        dominated_objectives=parsed.get("dominated_objectives", []),
        partial_objectives=parsed.get("partial_objectives", []),
        not_understood_objectives=parsed.get("not_understood_objectives", []),
        review_recommendation=parsed.get("review_recommendation", "Revisar os objetivos nao compreendidos."),
        retrieved_context=context_chunks,
        llm_source=llm_source,
    )


def _fallback_consolidacao(
    objectives: list[str],
    dominated: list[str],
    not_understood: list[str],
) -> dict[str, object]:
    partial: list[str] = []
    if len(not_understood) > 1:
        partial = not_understood[:1]
        not_understood = not_understood[1:]

    question_pool = {
        "Limites": "O que significa dizer que o limite de uma funcao existe em um ponto?",
        "Regra de L'Hopital": "Quando podemos aplicar a Regra de L'Hopital em um limite?",
        "Derivada": "Como voce explicaria derivada como taxa de variacao instantanea?",
        "Regra da Cadeia": "Quando usamos a Regra da Cadeia na derivacao?",
    }

    questions: list[str] = []
    for topic in objectives[:5]:
        questions.append(question_pool.get(topic, f"Explique de forma simples o conceito de {topic}."))

    if not questions:
        questions = [
            "Explique com suas palavras o tema central da aula.",
            "Qual conceito voce considera mais dificil e por que?",
            "Resolva um exemplo simples aplicando o conceito principal.",
        ]

    if not dominated and objectives:
        dominated = objectives[:1]
    if not not_understood and len(objectives) > len(dominated):
        not_understood = objectives[len(dominated):]

    review_target = ", ".join(not_understood or partial) or "os topicos principais da aula"
    review = (
        f"Revisar {review_target} com resumo teorico curto, 3 exercicios basicos e correcao comentada."
    )

    return {
        "consolidation_questions": questions[:5],
        "dominated_objectives": dominated,
        "partial_objectives": partial,
        "not_understood_objectives": not_understood,
        "review_recommendation": review,
    }


def _parse_consolidacao_json(raw_text: str) -> dict[str, object] | None:
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
