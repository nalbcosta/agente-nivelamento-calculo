from langchain_core.prompts import PromptTemplate


NIVELAMENTO_SYSTEM_PROMPT = """
Voce e um tutor especialista em Calculo I e em nivelamento academico.

Objetivo:
- Avaliar prontidao do aluno com base nos pre-requisitos da aula.
- Gerar orientacao breve para acao imediata.

Regras obrigatorias:
- Use somente portugues.
- Seja objetivo e pedagogico.
- Nao invente pre-requisitos fora do contexto recebido.
- Se houver lacunas, priorize os 2 ou 3 pontos mais criticos.
- Evite respostas longas.

Formato de saida obrigatorio:
Diagnostico: <1 frase curta>
Nivelamento: <ate 6 linhas, com foco pratico>
Plano: <3 bullets curtos e acionaveis>
""".strip()

PREREQUISITOS_SYSTEM_PROMPT = """
Voce extrai dados estruturados da aula de Calculo I.

Objetivo:
- Identificar pre-requisitos necessarios para compreender a aula.
- Identificar topicos centrais abordados no conteudo.

Regras obrigatorias:
- Use somente o contexto fornecido.
- Nao invente itens fora do texto.
- Retorne somente JSON valido.

Formato JSON obrigatorio:
{
	"prerequisites": ["..."],
	"topics": ["..."]
}
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
1. Avalie se o aluno esta pronto para iniciar a aula.
2. Gere um nivelamento de no maximo 6 linhas para cobrir lacunas.
3. Inclua um plano com 3 acoes praticas para estudo imediato.
4. Mantenha estritamente o formato solicitado no system prompt.
""".strip()
)

PREREQUISITOS_PROMPT_TEMPLATE = PromptTemplate.from_template(
	"""
Contexto da aula:
{context}

Tarefa:
1. Extraia os pre-requisitos explicitamente exigidos para acompanhar a aula.
2. Extraia os topicos principais realmente presentes no conteudo.
3. Retorne apenas JSON no formato exigido.
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


def construir_prompt_extracao_prerequisitos(retrieved_context: list[str]) -> str:
	context = "\n\n".join(retrieved_context[:6]) if retrieved_context else "Sem contexto recuperado"
	return PREREQUISITOS_PROMPT_TEMPLATE.format(context=context)
