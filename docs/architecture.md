# Arquitetura — Agente de Nivelamento Cálculo I

## Visão geral

O sistema é composto por três camadas principais: um frontend Next.js, uma API FastAPI com serviços especializados por case, e um banco PostgreSQL com a extensão pgvector para busca semântica.

```mermaid
flowchart TD
    subgraph UI["Frontend — Next.js :3000"]
        NP["NivelamentoPanel\n(Case 1)"]
        CP["ConsolidacaoPanel\n(Case 2)"]
        FP["FlashcardsPanel\n(Case 3)"]
        MT["MathText\n(KaTeX rendering)"]
    end

    subgraph API["Backend — FastAPI :8000"]
        R["/api/v1 Router"]
        NS["NivelamentoService"]
        CS["ConsolidacaoService"]
        DS["DiagnosticoService"]
        FS["FlashcardService"]
        IS["IngestionService"]
        LS["LLM Service\n(fallback chain)"]
        ES["EmbeddingService\n(gemini-embedding-2)"]
    end

    subgraph DB["PostgreSQL :5432 (interno) / :5438 (host)"]
        DC[("document_chunks\n+ pgvector index")]
        ST[("students")]
        SR[("student_readiness")]
        SM[("student_memorized_concepts")]
    end

    subgraph LLM["LLM — fallback em cadeia"]
        G["① Gemini\ngemini-flash-lite-latest"]
        GR["② Groq\nllama-3.1-8b-instant"]
        HF["③ Hugging Face\nLlama-3.1-8B-Instruct"]
        OL["④ Ollama\nllama3.1:8b (local)"]
        FB["⑤ Heurística\ndeterminística"]
        G -->|falha| GR -->|falha| HF -->|falha| OL -->|falha| FB
    end

    NP & CP & FP -->|HTTP REST| R
    R --> NS & CS & DS & FS
    NS & CS & DS & FS --> LS --> LLM
    NS --> IS --> ES
    NS & CS & FS --> ES -->|cosine similarity| DC
    NS --> SR
    CS --> ST
    FS --> SM
    NP & CP & FP --> MT
```

---

## Pipeline RAG (Retrieval-Augmented Generation)

Toda resposta do LLM é ancorada em trechos reais da aula. Isso elimina alucinação de pré-requisitos e garante que as perguntas de consolidação e os flashcards sejam baseados no conteúdo que o aluno de fato estudou.

```mermaid
flowchart LR
    MD["calculo_i_aula.md"]
    CH["Chunking\n(parágrafos / seções)"]
    EM["EmbeddingService\ngemini-embedding-2\n1536 dims MRL"]
    VDB[("pgvector\nivfflat index")]
    QE["Query Embedding\n(background + tópicos do aluno)"]
    TS["Top-K chunks\n(cosine distance)"]
    PR["Prompt\n= contexto da aula\n+ perfil do aluno\n+ instrução do case"]
    LM["LLM\n(Gemini JSON mode)"]
    RS["Response\n(JSON estruturado)"]

    MD --> CH --> EM --> VDB
    QE --> VDB -->|"SELECT ... ORDER BY\nembedding <=> query_embedding"| TS
    TS --> PR --> LM --> RS
```

### Parâmetros de ingestão

| Parâmetro | Valor |
|---|---|
| Modelo de embedding | `gemini-embedding-2` |
| Dimensionalidade | 1536 (MRL-truncated) |
| Índice pgvector | `ivfflat` (cosine) |
| Rota de ingestão | `POST /api/v1/nivelamento/ingest` |
| Chunks indexados | ~18 (aula atual) |

---

## Cadeia de fallback do LLM

O `LLM_PROVIDER` no `.env` define o provider primário. Se a chamada falhar por qualquer motivo (rate limit, timeout, ausência de chave), o `LLMService` tenta automaticamente o próximo na cadeia:

```
① Gemini  (gemini-flash-lite-latest)   ← padrão; suporta JSON mode nativo
  └─▶ ② Groq  (llama-3.1-8b-instant)
        └─▶ ③ Hugging Face (Llama-3.1-8B-Instruct via Inference API)
              └─▶ ④ Ollama local (llama3.1:8b)
                    └─▶ ⑤ Heurística determinística (sem LLM — nunca retorna 500)
```

Para endpoints que produzem JSON estruturado (flashcards, consolidação, extração de pré-requisitos), o Gemini recebe `responseMimeType: "application/json"` na `generationConfig`. Isso elimina a necessidade de regex de extração e parse tolerante a falhas.

---

## Fluxo de requisição — Case 1 (Nivelamento)

```mermaid
sequenceDiagram
    actor Aluno
    participant FE as Frontend (Next.js)
    participant API as FastAPI
    participant VDB as pgvector
    participant LLM as Gemini

    Aluno->>FE: Informa student_id, background e known_topics
    FE->>API: GET /students/{id}  ← pré-carrega perfil salvo
    API-->>FE: Perfil anterior (tópicos, background)

    Aluno->>FE: Clica "Analisar Nivelamento"
    FE->>API: POST /nivelamento
    API->>VDB: Embedding da query → cosine search → top-k chunks
    VDB-->>API: Trechos da aula mais relevantes
    API->>LLM: Prompt (contexto RAG + perfil do aluno)
    LLM-->>API: {is_ready, prerequisites, missing, support_text} (JSON mode)
    API->>VDB: INSERT student_readiness
    API-->>FE: NivelamentoResponse
    FE->>Aluno: ✅ Pronto ou ⚠️ Plano de nivelamento
```

---

## Fluxo de requisição — Case 2 (Consolidação + Diagnóstico)

```mermaid
sequenceDiagram
    actor Aluno
    participant FE as Frontend (Next.js)
    participant API as FastAPI
    participant DB as PostgreSQL
    participant LLM as Gemini

    note over FE,LLM: Fase 1 — Geração de perguntas inéditas
    Aluno->>FE: Clica "Gerar Perguntas"
    FE->>API: POST /consolidacao {answered_questions: []}
    API->>DB: SELECT consolidation_history_json FROM students WHERE student_id=?
    DB-->>API: Lista de perguntas já feitas anteriormente
    API->>LLM: Prompt (RAG + histórico) — instrução para não repetir
    LLM-->>API: 3–5 perguntas novas (JSON mode)
    API->>DB: UPSERT students (append perguntas ao histórico, deduplicated)
    API-->>FE: ConsolidacaoResponse {perguntas}

    note over FE,LLM: Fase 2 — Diagnóstico de compreensão
    Aluno->>FE: Responde as perguntas
    FE->>API: POST /diagnostico {consolidation_questions, answered_questions}
    API->>LLM: Avalia pares pergunta/resposta
    LLM-->>API: {dominados, parcialmente_compreendidos, nao_compreendidos, recomendacao}
    API-->>FE: DiagnosticoResponse
    FE->>Aluno: Mapa de objetivos + próximos passos
```

---

## Fluxo de requisição — Case 3 (Flashcards)

```mermaid
sequenceDiagram
    actor Aluno
    participant FE as Frontend (Next.js)
    participant API as FastAPI
    participant DB as PostgreSQL
    participant LLM as Gemini

    Aluno->>FE: Digita student_id
    FE->>API: GET /students/{id}
    DB-->>FE: memorized_concepts (conceitos já persistidos)
    FE->>Aluno: Exibe conceitos memorizados anteriormente

    Aluno->>FE: Clica "Gerar Flashcards"
    FE->>API: POST /flashcards {student_id, memorized_concepts}
    API->>DB: SELECT concept FROM student_memorized_concepts WHERE student_id=?
    API->>LLM: Gera flashcards excluindo conceitos já memorizados
    LLM-->>API: [{pergunta, resposta, conceito}, ...] (JSON mode)
    API-->>FE: FlashcardResponse

    Aluno->>FE: Marca conceito como "Memorizado"
    FE->>API: POST /flashcards {memorized_concepts: [..., novo_conceito]}
    API->>DB: INSERT student_memorized_concepts (UNIQUE: student_id + normalized_concept)
    note right of DB: Conceito nunca volta a aparecer\npara este aluno em sessões futuras
```

---

## Modelo de dados

```mermaid
erDiagram
    students {
        int id PK
        string student_id UK
        text background
        text known_topics_json
        text consolidation_history_json
        datetime created_at
        datetime updated_at
    }

    student_readiness {
        int id PK
        string student_id FK
        bool is_ready
        text gaps_summary
        text support_text
        datetime created_at
    }

    student_memorized_concepts {
        int id PK
        string student_id FK
        string concept
        string normalized_concept UK
        datetime created_at
    }

    document_chunks {
        int id PK
        string source
        int chunk_index
        text chunk_text
        vector embedding
        string prerequisite_tag
        datetime created_at
    }

    students ||--o{ student_readiness : "tem histórico de prontidão"
    students ||--o{ student_memorized_concepts : "tem conceitos memorizados"
```

### Responsabilidade de cada tabela

| Tabela | Case | Propósito |
|---|---|---|
| `document_chunks` | RAG (todos) | Chunks da aula de Cálculo I com embeddings vetoriais (pgvector) |
| `student_readiness` | Case 1 | Histórico de avaliações de prontidão por aluno |
| `students` | Case 2 | Perfil do aluno: background, tópicos, histórico de perguntas de consolidação |
| `student_memorized_concepts` | Case 3 | Conceitos já memorizados por aluno — tabela separada para queries eficientes |

---

## Persistência de perfil do aluno

```
POST /nivelamento  ──▶  student_readiness (histórico de prontidão)
POST /consolidacao ──▶  students.consolidation_history_json (deduplica perguntas por sessão)
POST /flashcards   ──▶  student_memorized_concepts (UPSERT com unique constraint)
GET  /students/:id ──▶  perfil completo → pré-preenchimento automático no frontend
```

O frontend detecta automaticamente o perfil salvo ao digitar o `student_id` e pré-preenche tópicos conhecidos, background e conceitos memorizados. Um banner indica ao aluno o que foi carregado do histórico.

---

## Renderização de fórmulas matemáticas

O frontend usa KaTeX para renderizar expressões LaTeX presentes nas respostas do LLM. O componente `MathText` faz o parse do texto, identifica delimitadores `$...$` (inline) e `$$...$$` (display mode) e delega cada segmento ao KaTeX antes de renderizar o HTML.

Exemplos de fórmulas renderizadas:

- Limite: $\lim_{x \to a} \frac{f(x) - f(a)}{x - a}$
- Derivada pela regra da cadeia: $\frac{d}{dx}[f(g(x))] = f'(g(x)) \cdot g'(x)$
- Regra do produto: $(fg)' = f'g + fg'$

