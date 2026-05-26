from langchain_core.prompts import PromptTemplate


NIVELAMENTO_SYSTEM_PROMPT = """
Voce e um tutor de Calculo I. Extraia pre-requisitos da aula e avalie prontidao do aluno.
Responda de forma breve, clara e acionavel.
""".strip()

NIVELAMENTO_PROMPT_TEMPLATE = PromptTemplate.from_template(
	"""
Contexto da aula (evidencias):
{context}

Perfil do aluno:
- Background: {student_background}
- Topicos conhecidos: {known}

Diagnostico parcial:
- Pre-requisitos extraidos: {prereq}
- Lacunas identificadas: {missing}

Tarefa:
1. Gere um diagnostico curto de prontidao.
2. Gere um conteudo breve de nivelamento com no maximo 6 linhas.
3. Seja objetivo, pedagogico e acionavel.
""".strip()
)


def construir_prompt_nivelamento(
	student_background: str,
	known_topics: list[str],
	extracted_prerequisites: list[str],
	missing_prerequisites: list[str],
	retrieved_context: list[str],
) -> str:
	known = ", ".join(known_topics) if known_topics else "nenhum topico informado"
	prereq = ", ".join(extracted_prerequisites) if extracted_prerequisites else "nao identificado"
	missing = ", ".join(missing_prerequisites) if missing_prerequisites else "nenhum"

	context = "\n\n".join(retrieved_context[:4]) if retrieved_context else "Sem contexto recuperado"

	return NIVELAMENTO_PROMPT_TEMPLATE.format(
		context=context,
		student_background=student_background or "nao informado",
		known=known,
		prereq=prereq,
		missing=missing,
	)
