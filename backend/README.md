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

4. Ajuste `.env` para usar LLM real:

- `LLM_PROVIDER=huggingface` ou `LLM_PROVIDER=ollama`
- `HUGGINGFACE_API_TOKEN` quando `huggingface`
- `HUGGINGFACE_CHAT_MODEL` conforme seu modelo
- `OLLAMA_BASE_URL` e `OLLAMA_CHAT_MODEL` quando `ollama`

## Executar API

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Usando Docker Compose

O `docker-compose.yml` monta a pasta `./data` do projeto em `/app/data` no container.
Isso garante que o arquivo `calculo_i_aula.md` esteja disponível para o backend.

## Swagger / OpenAPI

Após subir o backend, acesse:

- Swagger UI: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

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
