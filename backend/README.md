# Backend

Base inicial do backend com FastAPI, SQLAlchemy, LangChain e suporte a LLM.

## Estrutura

- `app/main.py`: aplicação FastAPI
- `app/core/config.py`: configurações e variáveis de ambiente
- `app/db/`: sessão, modelos e bootstrap de banco
- `app/api/routes.py`: endpoints da API
- `alembic/`: ambiente e versões de migração
- `alembic.ini`: configuração do Alembic
- `scripts/test_nivelamento.py`: script de ingestão e teste do fluxo de nivelamento
- `scripts/test_consolidacao.py`: script de teste do fluxo de consolidacao de aprendizagem
- `scripts/test_flashcards.py`: script de teste do fluxo de memorização com flashcards

## Ambiente

1. Entre no diretório do backend:

```powershell
cd backend
```

2. Instale as dependências:

```powershell
python -m pip install -e .
```

3. Copie o exemplo de variáveis de ambiente:

```powershell
copy .env.example .env
```

4. Ajuste `.env` para usar Gemini ou outro LLM:

```env
# Primário (padrão):
LLM_PROVIDER=gemini
GEMINI_API_TOKEN=AIzaSy...
GEMINI_CHAT_MODEL=gemini-flash-lite-latest
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
EMBEDDING_PROVIDER=gemini

# Fallbacks alternativos:
# LLM_PROVIDER=groq
# GROQ_API_TOKEN=gsk_...
# ou
# LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
```

## Executar API

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Usando Docker Compose

O `docker-compose.yml` monta a pasta `./data` do projeto em `/app/data` no container.
Isso garante que o arquivo `calculo_i_aula.md` esteja disponível para o backend.

## Swagger / OpenAPI e Exemplos

Após subir o backend, acesse:

- Swagger UI: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

Para exemplos completos de curl de todos os endpoints, veja [docs/api-examples.md](../docs/api-examples.md)

## Testando o fluxo de nivelamento

1. Inicie o backend:

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. Execute o script de teste:

```powershell
python scripts/test_nivelamento.py --backend-url http://localhost:8000
```

3. Exemplos de payload usados no script:

```json
{
  "student_id": "aluno_001",
  "student_background": "Conheco funcoes, regras de potencia e trigonometria.",
  "known_topics": ["Funcoes", "Regras de Potencia e Algebra", "Trigonometria"]
}
```

## Endpoints principais

- `POST /api/v1/nivelamento`
- `POST /api/v1/consolidacao`
- `POST /api/v1/flashcards`
- `POST /api/v1/nivelamento/ingest`

## Testando o fluxo de consolidacao

1. Inicie o backend:

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. Execute o script de teste:

```powershell
python scripts/test_consolidacao.py --backend-url http://localhost:8000
```

3. Exemplo de payload usado no script:

```json
{
  "student_id": "aluno_001",
  "student_background": "Conheco limites e derivadas basicas, mas tenho duvidas na regra da cadeia.",
  "known_topics": ["Limites", "Derivada"],
  "answered_questions": [
    "Derivada e a taxa de variacao instantanea.",
    "Tenho dificuldade para identificar quando usar regra da cadeia."
  ]
}
```

## Testando o fluxo de flashcards

1. Inicie o backend:

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. Execute o script de teste:

```powershell
python scripts/test_flashcards.py --backend-url http://localhost:8000
```

3. Exemplo de payload usado no script:

```json
{
  "student_id": "aluno_flashcard_001",
  "student_background": "Ja estudei limites e derivadas basicas, mas erro aplicacao da regra da cadeia.",
  "known_topics": ["Limites", "Derivada"],
  "memorized_concepts": ["Limites", "Derivada"],
  "target_flashcards": 5
}
```

## Status de implementacao dos cases

- Case 1 (nivelamento): extracao de pre-requisitos e topicos em modo LLM-first com fallback estatico.
- Case 2 (consolidacao): fluxo com perguntas, classificacao por objetivos e recomendacao de revisao.
  Fallback final tambem considera respostas do aluno (`answered_questions`) para classificar objetivos como parciais.
- Case 3 (flashcards): geracao via LLM com fallback local e persistencia de conceitos memorizados para evitar repeticao.

## Validacao dos 3 cases em integracao real

Os scripts abaixo rodam contra API real (sem monkeypatch), ingerem a aula `data/calculo_i_aula.md`
e validam requisitos minimos de cada case com checks de sucesso/erro:

- `scripts/test_nivelamento.py`
- `scripts/test_consolidacao.py`
- `scripts/test_flashcards.py`

## Testes automatizados

Executar toda a suite:

```powershell
cd backend
agente\Scripts\python.exe -m pytest tests -q
```

Arquivos de teste principais:

- `tests/test_nivelamento_api.py`
- `tests/test_consolidacao_api.py`
- `tests/test_flashcards_api.py`

## Benchmark de taxa de fallback (Case 3)

Objetivo: medir a taxa de respostas com `llm_source=fallback` em 10 chamadas reais.

Comando usado:

```powershell
cd backend
@'
import httpx, json
base='http://localhost:8000/api/v1'
client=httpx.Client(timeout=60.0)
client.post(f'{base}/nivelamento/ingest')
results=[]
for i in range(10):
  payload={
    'student_id':f'benchmark_flash_{i}',
    'student_background':'Tenho base inicial em calculo.',
    'known_topics':[],
    'memorized_concepts':[],
    'target_flashcards':3,
  }
  r=client.post(f'{base}/flashcards', json=payload)
  r.raise_for_status()
  data=r.json()
  results.append({'i':i,'llm_source':data.get('llm_source'),'cards':len(data.get('flashcards',[]))})
summary={
  'total':len(results),
  'llm_hits':sum(1 for x in results if x['llm_source']!='fallback'),
  'fallback_hits':sum(1 for x in results if x['llm_source']=='fallback'),
  'avg_cards':sum(x['cards'] for x in results)/len(results),
  'results':results,
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
'@ | agente\Scripts\python.exe -
```

Ultima medicao registrada:

- Execucao final com cache de resposta e Groq: `llm_hits=10`, `fallback_hits=0`.
- Interpretacao: as respostas passaram a usar o modelo de forma consistente no benchmark de 10 chamadas.

## Alembic

Mostrar historico de revisoes:

```powershell
cd backend
agente\Scripts\alembic.exe history
```

Aplicar migracoes:

```powershell
cd backend
agente\Scripts\alembic.exe upgrade head
```

Criar nova revisao com autogenerate:

```powershell
cd backend
agente\Scripts\alembic.exe revision --autogenerate -m "descricao"
```
