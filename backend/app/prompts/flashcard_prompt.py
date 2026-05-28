from langchain_core.prompts import PromptTemplate


FLASHCARD_SYSTEM_PROMPT = """
Voce e um agente de memorizacao para Calculo I em formato de flashcards.

Objetivo:
- Reforcar conceitos que o aluno ainda nao memorizou.
- Priorizar dificuldades recorrentes e erros conceituais.

Regras:
- Use portugues simples e tecnicamente correto.
- Cada flashcard deve ter frente curta e verso objetivo.
- Inclua 1 exemplo pratico no verso quando fizer sentido.
- Evite repeticao de flashcards equivalentes.
- O campo concept deve repetir exatamente um dos conceitos pendentes fornecidos.
- Limite o verso a no maximo 160 caracteres.
- Nao inclua formulas longas, markdown ou explicacoes extensas.

Formato de saida:
- Retorne somente JSON valido, sem texto adicional.

Formato JSON obrigatorio:
{
  "flashcards": [
    {
      "concept": "...",
      "front": "...",
      "back": "..."
    }
  ]
}
""".strip()


FLASHCARD_PROMPT_TEMPLATE = PromptTemplate.from_template(
	"""
Aluno: {student_id}

Contexto da aula (evidencias):
{context}

Perfil do aluno:
- Background: {student_background}
- Topicos conhecidos: {known_topics}

Conceitos pendentes para gerar flashcards:
{pending_concepts}

Tarefa:
1. Gere exatamente 1 flashcard por conceito pendente informado.
2. Frente curta e objetiva (pergunta).
3. Verso direto, com definicao correta e uma dica pratica curta, respeitando o limite de tamanho.
4. No campo concept, repita exatamente o texto do conceito pendente correspondente.
5. Retorne somente JSON no formato exigido.
""".strip()
)


def construir_prompt_flashcards(
	student_id: str,
	student_background: str,
	known_topics: list[str],
	retrieved_context: list[str],
	pending_concepts: list[str],
) -> str:
	context = "\n\n".join(retrieved_context[:4]) if retrieved_context else "Sem contexto recuperado"
	known = ", ".join(known_topics) if known_topics else "nenhum topico informado"
	concepts = ", ".join(pending_concepts) if pending_concepts else "nenhum"

	return FLASHCARD_PROMPT_TEMPLATE.format(
		student_id=student_id,
		context=context,
		student_background=student_background or "nao informado",
		known_topics=known,
		pending_concepts=concepts,
	)
