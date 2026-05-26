# Backend

Base inicial do backend com FastAPI, SQLAlchemy e Alembic.

## Estrutura

- src/app/main.py: aplicacao FastAPI
- src/app/core/config.py: configuracoes e variaveis de ambiente
- src/app/db/: sessao, modelos e bootstrap de banco
- src/app/api/routes.py: endpoints iniciais
- alembic/: ambiente e versoes de migracao
- alembic.ini: configuracao do Alembic

## Ambiente

Use o virtualenv ja criado em backend/agente.

Variaveis suportadas (arquivo .env em backend):

- APP_NAME
- APP_VERSION
- API_V1_PREFIX
- DATABASE_URL

Exemplo em .env.example.

## Instalar dependencias

```powershell
cd backend
agente\Scripts\python.exe -m pip install -e .
```

## Executar API

```powershell
cd backend
agente\Scripts\uvicorn.exe app.main:app --reload --app-dir src
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
