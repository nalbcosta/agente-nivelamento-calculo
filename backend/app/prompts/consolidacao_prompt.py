from langchain_core.prompts import PromptTemplate


CONSOLIDACAO_SYSTEM_PROMPT = """
Voce e um tutor de Calculo I focado em consolidacao de aprendizagem apos a aula.

Objetivo:
- Gerar perguntas simples para verificar compreensao.
- Classificar objetivos de conhecimento em dominados, parciais e nao compreendidos.
- Recomendar revisao objetiva para lacunas.

Regras:
- Use apenas portugues.
- Seja claro, curto e pedagogico.
- Nao invente objetivos fora do contexto da aula.
- Gere no minimo 3 e no maximo 5 perguntas simples.
- Retorne somente JSON valido, sem texto adicional.

Formato JSON obrigatorio:
{
  "consolidation_questions": ["..."],
  "dominated_objectives": ["..."],
  "partial_objectives": ["..."],
  "not_understood_objectives": ["..."],
  "review_recommendation": "..."
}
""".strip()

CONSOLIDACAO_PROMPT_TEMPLATE = PromptTemplate.from_template(
    """
Contexto da aula (evidencias):
{context}

Perfil do aluno:
- Background: {student_background}
- Topicos conhecidos: {known_topics}
- Respostas do aluno: {answered_questions}

Objetivos detectados na aula:
{objectives}

Diagnostico inicial (heuristico):
- Dominados: {dominated_initial}
- Nao compreendidos: {not_understood_initial}

Tarefa:
1. Gere de 3 a 5 perguntas simples de consolidacao.
2. Classifique objetivos em dominados, parciais e nao compreendidos.
3. Gere recomendacao de revisao focada nas lacunas.
4. Retorne somente o JSON no formato especificado.
""".strip()
)


def construir_prompt_consolidacao(
    student_background: str,
    known_topics: list[str],
    answered_questions: list[str],
    objectives: list[str],
    dominated_initial: list[str],
    not_understood_initial: list[str],
    retrieved_context: list[str],
) -> str:
    context = "\n\n".join(retrieved_context[:4]) if retrieved_context else "Sem contexto recuperado"
    known = ", ".join(known_topics) if known_topics else "nenhum topico informado"
    answers = " | ".join(answered_questions) if answered_questions else "nenhuma resposta informada"
    objs = ", ".join(objectives) if objectives else "objetivos nao detectados"
    dom = ", ".join(dominated_initial) if dominated_initial else "nenhum"
    not_understood = ", ".join(not_understood_initial) if not_understood_initial else "nenhum"

    return CONSOLIDACAO_PROMPT_TEMPLATE.format(
        context=context,
        student_background=student_background or "nao informado",
        known_topics=known,
        answered_questions=answers,
        objectives=objs,
        dominated_initial=dom,
        not_understood_initial=not_understood,
    )
