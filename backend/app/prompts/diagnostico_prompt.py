DIAGNOSTICO_SYSTEM_PROMPT = """
Voce avalia a consolidacao da aprendizagem apos a aula de Calculo I.

Objetivo:
- Classificar dominio dos objetivos de aprendizagem.
- Indicar lacunas e recomendar revisao direcionada.

Regras:
- Use portugues claro e direto.
- Nao invente resultados nao suportados pelas evidencias.
- Justifique brevemente cada classificacao com evidencias observadas.

Escala obrigatoria por objetivo:
- Dominado
- Parcial
- Nao dominado

Formato de saida:
Resumo: <2 frases maximo>
Objetivos: <lista com classificacao e justificativa curta>
Revisao sugerida: <3 bullets de acao>
""".strip()


def construir_prompt_diagnostico(
	student_background: str,
	known_topics: list[str],
	answered_questions: list[str],
	objectives: list[str],
	dominated_initial: list[str],
	partial_initial: list[str],
	not_understood_initial: list[str],
	retrieved_context: list[str],
) -> str:
	context = "\n".join(f"- {item}" for item in retrieved_context[:4])
	known = ", ".join(known_topics) if known_topics else "(vazio)"
	answers = "\n".join(f"- {ans}" for ans in answered_questions[:8]) or "- (sem respostas)"

	return f"""
BACKGROUND DO ALUNO:
{student_background or "(nao informado)"}

TOPICOS CONHECIDOS:
{known}

RESPOSTAS DO ALUNO:
{answers}

OBJETIVOS DETECTADOS:
{", ".join(objectives) if objectives else "(nao detectados)"}

CLASSIFICACAO INICIAL:
- Dominado: {", ".join(dominated_initial) if dominated_initial else "(nenhum)"}
- Parcial: {", ".join(partial_initial) if partial_initial else "(nenhum)"}
- Nao dominado: {", ".join(not_understood_initial) if not_understood_initial else "(nenhum)"}

CONTEXTO RECUPERADO (RAG):
{context or "- (sem contexto)"}

Retorne EXCLUSIVAMENTE JSON valido no formato:
{{
  "summary": "...",
  "objectives": [
    {{"objective": "...", "status": "Dominado|Parcial|Nao dominado", "justification": "..."}}
  ],
  "review_actions": ["...", "...", "..."]
}}
""".strip()
