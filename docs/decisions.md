# Decisões Técnicas

Registro das principais decisões de arquitetura e design tomadas durante o desenvolvimento, com contexto e justificativa.

---

## 1. Multi-provider LLM com fallback em cadeia

**Decisão:** O `LLM_PROVIDER` no `.env` define o provider primário. Se a chamada falhar, o sistema tenta automaticamente o próximo na cadeia: Gemini → Groq → Hugging Face → Ollama local → heurística determinística.

**Justificativa:** Garante disponibilidade mesmo em ambientes sem acesso a todas as APIs (ex: sem chave Groq, mas com HuggingFace gratuito). O fallback determinístico garante que o endpoint nunca retorna 500 — apenas degrada graciosamente.

**Trade-off:** A heurística local (fallback final) produz resultados de qualidade inferior, mas é aceitável como último recurso em demo/CI.

---

## 2. Gemini JSON Mode para saídas estruturadas

**Decisão:** Para os endpoints que produzem JSON (flashcards, consolidação, extração de pré-requisitos), a chamada ao Gemini inclui `responseMimeType: "application/json"` na `generationConfig`.

**Justificativa:** Sem JSON mode, LLMs frequentemente adicionam texto antes ou depois do JSON (`"Aqui está o resultado: {...}"`) ou truncam o objeto quando o limite de tokens é atingido. O JSON mode força o modelo a gerar somente JSON válido, eliminando a necessidade de regex de extração e a cadeia de fallbacks de parse.

**Alternativa descartada:** Parse tolerante com `json.loads` + regex + `_build_single_flashcard_from_plain_text` — implementado inicialmente mas removido após ativar o JSON mode.

---

## 3. pgvector com embeddings de 1536 dimensões (MRL)

**Decisão:** O modelo `gemini-embedding-2` (Google) gera embeddings com dimensão configurável via MRL (Matryoshka Representation Learning). Usamos 1536 dims com índice `ivfflat`.

**Justificativa:** O modelo Gemini embedding supera o `all-MiniLM-L6-v2` (384 dims, HuggingFace) em qualidade semântica para textos em português e fórmulas matemáticas. O MRL permite truncar para menor dimensão sem retreinar caso performance seja necessária.

**Trade-off:** Requer chave de API Gemini; o `all-MiniLM-L6-v2` roda localmente via HuggingFace sem custo. Ambos os providers são suportados via `EMBEDDING_PROVIDER` no `.env`.

---

## 4. Persistência de perguntas de consolidação para evitar repetição

**Decisão:** As perguntas geradas pelo Case 2 são armazenadas em `students.consolidation_history_json`. O prompt do LLM recebe esse histórico com instrução explícita para não repetir.

**Justificativa:** Sem persistência, o mesmo aluno recebe as mesmas perguntas a cada sessão, tornando a consolidação ineficaz. O histórico garante que cada sessão avance o aprendizado cobrindo novos ângulos.

**Implementação:** O campo é um array JSON deduplicated antes de cada upsert. O LLM não recebe diretamente as respostas anteriores — apenas as perguntas — para não enviesar o diagnóstico com contexto stale.

---

## 5. Conceitos memorizados em tabela separada

**Decisão:** Os conceitos marcados como memorizados no Case 3 ficam em `student_memorized_concepts` (tabela separada), não em um campo JSON no `students`.

**Justificativa:** Permite queries eficientes para filtrar conceitos por aluno sem deserializar JSON. Facilita remoção individual de um conceito (e.g., "esqueci esse conceito, quero rever") sem reescrever o array inteiro.

---

## 6. Frontend: fluxo sequencial com stepper

**Decisão:** A UI apresenta os 3 cases como etapas numeradas (① Nivelamento → ② Consolidação → ③ Flashcards). Após completar cada etapa, um CTA aparece sugerindo a próxima.

**Justificativa:** O fluxo pedagógico correto é pré-aula → pós-aula → memorização. Apresentar os cases como tabs independentes sem hierarquia visual incentiva uso fora de ordem. O stepper comunica a progressão sem bloquear o acesso livre (o aluno ainda pode navegar livremente).

---

## 7. Pré-carregamento automático do perfil do aluno

**Decisão:** Ao digitar o `student_id`, o frontend faz `GET /students/{id}` e pré-preenche os campos de tópicos conhecidos, background e conceitos memorizados. Um banner indica o que foi carregado.

**Justificativa:** Reduz atrito: o aluno não precisa re-informar seu perfil a cada sessão. A fonte de verdade fica no banco de dados, não no localStorage. O merge é aditivo (não sobrescreve dados locais não-conflitantes).

---

## 8. KaTeX para renderização de fórmulas

**Decisão:** O componente `MathText` usa KaTeX no cliente para renderizar `$...$` (inline) e `$$...$$` (display) presentes nas respostas do LLM.

**Justificativa:** Respostas do LLM sobre Cálculo I contêm expressões como $\lim_{x \to a} f(x)$, $\frac{d}{dx}[f(g(x))]$, etc. Sem renderização, o aluno vê LaTeX cru, o que prejudica a leitura. KaTeX é leve, roda no cliente sem dependência de servidor e suporta todo o subconjunto matemático necessário.

**Alternativa descartada:** MathJax — mais completo, mas pesado (~200 KB) e com API async mais complexa de integrar em componentes React síncronos.

---

## 9. FastAPI + SQLAlchemy + Alembic

**Decisão:** Backend em FastAPI com ORM SQLAlchemy (psycopg3) e migrações via Alembic.

**Justificativa:** FastAPI gera documentação OpenAPI automaticamente (útil para demo no Swagger UI em `/docs`). SQLAlchemy facilita a troca de banco sem reescrever queries (útil se for necessário migrar de PostgreSQL). Alembic garante que o esquema seja versionado e reproduzível.

---

## 10. Docker Compose com banco em porta não-padrão

**Decisão:** O PostgreSQL expõe a porta `5438` no host (não `5432`).

**Justificativa:** Evita conflito com instâncias locais de PostgreSQL que desenvolvedores possam ter rodando. O backend dentro do Docker usa `db:5432` internamente — apenas o acesso externo (Adminer, scripts locais) usa 5438.
