# Exemplos de API

Exemplos de uso para todos os endpoints da API. O backend roda em `http://localhost:8000` por padrão.

Documentação interativa (Swagger UI): **http://localhost:8000/docs**

---

## Pré-requisito: ingerir a aula

Antes de executar os cases, ingira a aula de Cálculo I no banco de vetores. Só precisa ser feito uma vez (ou após atualizar o arquivo `.md`).

```bash
curl -s -X POST http://localhost:8000/api/v1/nivelamento/ingest | jq
```

Resposta esperada:
```json
{
  "status": "ok",
  "chunks_indexed": 18,
  "source": "calculo_i_aula.md"
}
```

---

## Case 1 — Nivelamento (pré-aula)

### Aluno sem pré-requisitos suficientes

```bash
curl -s -X POST http://localhost:8000/api/v1/nivelamento \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "demo_aluno_01",
    "student_background": "Tenho base em funções e álgebra, mas nunca estudei derivadas nem limites formalmente.",
    "known_topics": ["Funções", "Álgebra", "Trigonometria básica"]
  }' | jq
```

Resposta esperada:
```json
{
  "is_ready": false,
  "extracted_prerequisites": ["Limites", "Derivadas", "Regra da Cadeia", "..."],
  "missing_prerequisites": ["Limites", "Derivadas"],
  "detected_lesson_topics": ["Derivada por definição", "Regra do produto", "..."],
  "retrieved_context": ["...trecho da aula..."],
  "support_text": "**Plano de nivelamento em 3 ações:**\n\n* **Limites:** ...",
  "llm_source": "gemini"
}
```

### Aluno com todos os pré-requisitos

```bash
curl -s -X POST http://localhost:8000/api/v1/nivelamento \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "demo_aluno_02",
    "student_background": "Domino limites, derivadas e regra da cadeia.",
    "known_topics": ["Limites", "Derivadas", "Regra da Cadeia", "Funções"]
  }' | jq '.is_ready, .missing_prerequisites'
```

---

## Case 2 — Consolidação (pós-aula)

### Passo 1: gerar perguntas de consolidação

```bash
curl -s -X POST http://localhost:8000/api/v1/consolidacao \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "demo_aluno_01",
    "student_background": "Assisti a aula de derivadas.",
    "known_topics": ["Limites", "Derivadas"],
    "answered_questions": []
  }' | jq '.consolidation_questions'
```

Resposta esperada:
```json
[
  "Explique com suas palavras o que é a derivada de uma função.",
  "Qual a diferença entre a regra do produto e a regra da cadeia?",
  "Quando você usaria derivadas implícitas?"
]
```

### Passo 2: enviar respostas e obter diagnóstico

```bash
curl -s -X POST http://localhost:8000/api/v1/consolidacao \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "demo_aluno_01",
    "student_background": "Assisti a aula de derivadas.",
    "known_topics": ["Limites", "Derivadas"],
    "consolidation_questions": [
      "Explique com suas palavras o que é a derivada de uma função.",
      "Qual a diferença entre a regra do produto e a regra da cadeia?",
      "Quando você usaria derivadas implícitas?"
    ],
    "answered_questions": [
      "A derivada mede a taxa de variação instantânea.",
      "Não tenho certeza sobre a diferença.",
      ""
    ]
  }' | jq '{dominated: .dominated_objectives, partial: .partial_objectives, missing: .not_understood_objectives}'
```

Resposta esperada:
```json
{
  "dominated": ["Taxa de variação instantânea"],
  "partial": ["Regra do produto vs cadeia"],
  "missing": ["Derivadas implícitas"]
}
```

### Verificar que perguntas não se repetem (segunda sessão)

Execute o Passo 1 novamente com o mesmo `student_id`. As perguntas geradas serão diferentes das anteriores pois o histórico foi persistido.

---

## Case 3 — Flashcards (memorização)

### Primeira rodada (sem conceitos memorizados)

```bash
curl -s -X POST http://localhost:8000/api/v1/flashcards \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "demo_aluno_01",
    "student_background": "Tenho base em limites e derivadas básicas.",
    "known_topics": ["Limites", "Derivadas"],
    "memorized_concepts": [],
    "target_flashcards": 3
  }' | jq '{source: .llm_source, cards: [.flashcards[] | {concept, front}]}'
```

Resposta esperada:
```json
{
  "source": "gemini",
  "cards": [
    {"concept": "Derivada", "front": "Qual a interpretação geométrica da derivada de f(x) no ponto a?"},
    {"concept": "Regra da Cadeia", "front": "Como se aplica a regra da cadeia para derivar f(g(x))?"},
    {"concept": "Derivada Implícita", "front": "Quando usamos derivação implícita e como ela funciona?"}
  ]
}
```

### Segunda rodada (excluindo conceitos já memorizados)

```bash
curl -s -X POST http://localhost:8000/api/v1/flashcards \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "demo_aluno_01",
    "student_background": "Tenho base em limites e derivadas básicas.",
    "known_topics": ["Limites", "Derivadas"],
    "memorized_concepts": ["Derivada"],
    "target_flashcards": 3
  }' | jq '[.flashcards[].concept]'
```

"Derivada" não aparecerá na resposta — o agente gera cards apenas para conceitos ainda pendentes.

### Modo revisão (força repetição dos já memorizados)

```bash
curl -s -X POST http://localhost:8000/api/v1/flashcards \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "demo_aluno_01",
    "student_background": "...",
    "known_topics": ["Limites", "Derivadas"],
    "memorized_concepts": ["Derivada", "Limites"],
    "target_flashcards": 2,
    "review_mode": true
  }' | jq '{mode: "review", concepts: [.flashcards[].concept]}'
```

---

## Perfil do aluno

### Buscar perfil salvo

```bash
curl -s http://localhost:8000/api/v1/students/demo_aluno_01 | jq
```

Resposta esperada:
```json
{
  "student_id": "demo_aluno_01",
  "background": "Assisti a aula de derivadas.",
  "known_topics": ["Limites", "Derivadas"],
  "memorized_concepts": ["Derivada"],
  "previous_consolidation_questions": [
    "Explique com suas palavras o que é a derivada de uma função.",
    "Qual a diferença entre a regra do produto e a regra da cadeia?",
    "Quando você usaria derivadas implícitas?"
  ]
}
```

### Aluno novo (sem histórico)

```bash
curl -s http://localhost:8000/api/v1/students/aluno_que_nao_existe | jq
```

Retorna perfil vazio sem erro 404 — o aluno simplesmente ainda não tem dados persistidos.

---

## Health check

```bash
curl -s http://localhost:8000/api/v1/health
# {"status":"ok"}
```
