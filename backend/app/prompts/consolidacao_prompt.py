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
- Se houver perguntas anteriores indicadas, gere perguntas DIFERENTES delas.
- Se houver respostas do aluno, classifique os objetivos COM BASE nas respostas.
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

{qa_section}

Objetivos detectados na aula:
{objectives}

Diagnostico inicial (heuristico):
- Dominados: {dominated_initial}
- Nao compreendidos: {not_understood_initial}

{previous_questions_hint}

Tarefa:
1. Gere de 3 a 5 perguntas simples de consolidacao.
2. Classifique objetivos em dominados, parciais e nao compreendidos.
3. Se houver respostas do aluno acima, use-as para a classificacao — as respostas DEVEM impactar o diagnostico.
4. Gere recomendacao de revisao focada nas lacunas.
5. Retorne somente o JSON no formato especificado.
""".strip()
)


def construir_prompt_consolidacao(
    student_background: str,
    known_topics: list[str],
    consolidation_questions: list[str],
    answered_questions: list[str],
    objectives: list[str],
    dominated_initial: list[str],
    not_understood_initial: list[str],
    retrieved_context: list[str],
    previous_questions: list[str],
) -> str:
    context = "\n\n".join(retrieved_context[:4]) if retrieved_context else "Sem contexto recuperado"
    known = ", ".join(known_topics) if known_topics else "nenhum topico informado"
    objs = ", ".join(objectives) if objectives else "objetivos nao detectados"
    dom = ", ".join(dominated_initial) if dominated_initial else "nenhum"
    not_understood = ", ".join(not_understood_initial) if not_understood_initial else "nenhum"

    # Format Q&A pairs when both questions and answers are present
    if consolidation_questions and answered_questions:
        pairs = []
        for i, (q, a) in enumerate(zip(consolidation_questions, answered_questions), 1):
            pairs.append(f"Pergunta {i}: {q}\nResposta do aluno: {a.strip() or '(sem resposta)'}")
        qa_section = "Perguntas realizadas e respostas do aluno:\n" + "\n\n".join(pairs)
    else:
        qa_section = "Respostas do aluno: nenhuma resposta informada ainda."

    # Hint to avoid previously asked questions
    if previous_questions:
        recent = previous_questions[-15:]
        prev_list = "\n".join(f"- {q}" for q in recent)
        previous_questions_hint = (
            "IMPORTANTE: As perguntas abaixo JA foram feitas para este aluno em sessoes anteriores. "
            "Gere perguntas COMPLETAMENTE DIFERENTES:\n" + prev_list
        )
    else:
        previous_questions_hint = ""

    return CONSOLIDACAO_PROMPT_TEMPLATE.format(
        context=context,
        student_background=student_background or "nao informado",
        known_topics=known,
        qa_section=qa_section,
        objectives=objs,
        dominated_initial=dom,
        not_understood_initial=not_understood,
        previous_questions_hint=previous_questions_hint,
    )
