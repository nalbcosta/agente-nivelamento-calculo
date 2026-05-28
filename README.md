# Agente de Nivelamento — Cálculo I

Solução de agente de IA para personalização do aprendizado em Cálculo I. O sistema implementa os **3 cases** do desafio técnico: nivelamento pré-aula, consolidação de aprendizagem e memorização por flashcards. A aula fornecida (`calculo_i_aula.md`) é usada como base de conhecimento via RAG (Retrieval-Augmented Generation) com embeddings semânticos.

---

## Cases implementados

### Case 1 — Nivelamento (pré-aula)

O agente extrai os pré-requisitos da aula de Cálculo I via LLM e avalia se o aluno está apto a cursá-la com base no perfil informado.

**Diferencial:** quando o aluno possui lacunas, o agente gera um **conteúdo breve e explicativo** (nivelamento + plano de estudo em 3 ações) para prepará-lo antes de iniciar a aula.

### Case 2 — Consolidação de aprendizagem (pós-aula)

O agente gera de 3 a 5 perguntas de consolidação e, após receber as respostas do aluno, produz um diagnóstico de Objetivos de Conhecimento.

**Diferencial:** classifica os objetivos em **dominados**, **parcialmente compreendidos** e **não compreendidos**, gera uma **recomendação de revisão** personalizada e armazena o histórico de perguntas para **nunca repetir a mesma questão** em sessões futuras.

### Case 3 — Memorização por Flashcards (pós-aula)

O agente gera flashcards no estilo pergunta/resposta para os conceitos de Cálculo I. O aluno marca os conceitos que já memorizou e, nas próximas sessões, o agente cobra **apenas os conceitos ainda pendentes**.

**Diferencial:** a lista de conceitos memorizados é **persistida no banco de dados** por aluno — o sistema se adapta automaticamente a cada nova interação, sem repetir o que já foi assimilado.

---

## Tech stack

| Camada | Tecnologia |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Python 3.12, SQLAlchemy, Alembic |
| Banco de dados | PostgreSQL 18 + extensão pgvector |
| Embeddings / RAG | `sentence-transformers/all-MiniLM-L6-v2` via Hugging Face |
| LLM | Hugging Face Inference API → Groq → Ollama (fallback em cadeia) |
| Infra | Docker Compose, Adminer (admin DB) |

---

## Como rodar

### Pré-requisitos

- Docker e Docker Compose instalados
- Chave de API do Hugging Face (gratuita em [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)) — ou Groq API token para maior velocidade

### 1. Configurar variáveis de ambiente

```bash
cp backend/.env.example backend/.env
```

Edite `backend/.env` e preencha ao menos uma das chaves:

```env
HUGGINGFACE_API_TOKEN=hf_...      # Hugging Face (padrão)
# ou
GROQ_API_TOKEN=gsk_...            # Groq (mais rápido, recomendado para demo)
LLM_PROVIDER=groq                 # Trocar o provider padrão
```

### 2. Subir todos os serviços

```bash
docker compose up -d
```

Isso sobe:
- `db` — PostgreSQL na porta `5438` (host)
- `backend` — FastAPI na porta `8000`
- `adminer` — Admin do banco na porta `8080`

### 3. Acessar o frontend

O frontend de desenvolvimento roda fora do Docker:

```bash
cd frontend
pnpm install
pnpm dev
```

Acesse em **http://localhost:3000**

### 4. Verificar saúde do backend

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok"}
```

### Admin do banco (Adminer)

Acesse **http://localhost:8080** com:
- **Sistema**: PostgreSQL
- **Servidor**: `db`
- **Usuário**: `postgres`
- **Senha**: `postgres`
- **Base de dados**: `agente_nivelamento`

---

## Guia de demonstração

Use o perfil abaixo para uma demonstração completa em todos os cases:

**ID do aluno:** `demo_aluno_01`
**Background:** `Tenho base em funções e álgebra, mas nunca estudei derivadas nem limites formalmente.`
**Tópicos conhecidos:** `Funções, Álgebra, Trigonometria básica`

### Case 1 — Nivelamento

1. Selecione **Case 1 - Nivelamento** e preencha o perfil acima
2. Clique em **Analisar Nivelamento**
3. O agente identifica que **Limites** e **Derivadas** são pré-requisitos ausentes
4. A seção **Conteúdo de Nivelamento** exibe um plano em 3 ações para suprir as lacunas
5. Teste novamente adicionando `Limites, Derivadas` aos tópicos conhecidos — o agente confirma prontidão total

### Case 2 — Consolidação

1. Selecione **Case 2 - Consolidação**
2. Clique em **Gerar Perguntas** — 3 a 5 questões são geradas com base na aula
3. Responda as perguntas (pode responder de forma incompleta para ver a classificação de lacunas)
4. Clique em **Analisar meu aprendizado** — o diagnóstico mostra objetivos dominados, parciais e não compreendidos
5. Execute o fluxo novamente com o mesmo aluno — as perguntas geradas serão **diferentes** das anteriores

### Case 3 — Flashcards

1. Selecione **Case 3 - Flashcards** e defina **Conceitos já memorizados**: `Limites`
2. Clique em **Gerar Flashcards** — o agente gera cards apenas para conceitos pendentes
3. Na sessão de cards, marque um conceito como **Memorizado**
4. Gere novamente — o conceito marcado **não aparecerá mais**
5. Troque o ID do aluno (ex: `demo_aluno_02`) — o agente inicia do zero, sem herdar a memória

---

## Estrutura do projeto

```
agente-nivelamento-calculo/
├── backend/
│   ├── app/
│   │   ├── api/routes.py           # Endpoints FastAPI
│   │   ├── services/               # Lógica de negócio dos 3 cases
│   │   ├── prompts/                # Templates de prompt LLM
│   │   ├── db/models.py            # ORM: Student, StudentMemorizedConcept, etc.
│   │   └── core/config.py          # Configurações via .env
│   ├── alembic/                    # Migrações de banco
│   └── data/calculo_i_aula.md      # Aula de Cálculo I (base de conhecimento)
├── frontend/
│   └── app/
│       ├── page.tsx                # Página principal (estado global)
│       └── components/             # NivelamentoPanel, ConsolidacaoPanel, FlashcardsPanel
├── docs/
│   └── architecture.md             # Diagrama de arquitetura
└── docker-compose.yml
```

---

## Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/nivelamento` | Avalia prontidão do aluno (Case 1) |
| `POST` | `/api/v1/consolidacao` | Gera perguntas / diagnóstico (Case 2) |
| `POST` | `/api/v1/flashcards` | Gera e filtra flashcards (Case 3) |
| `GET` | `/api/v1/students/{id}` | Retorna perfil e histórico do aluno |

Documentação interativa disponível em **http://localhost:8000/docs** (Swagger UI).

