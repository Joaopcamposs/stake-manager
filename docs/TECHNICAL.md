# Bet Tracker — Documentação Técnica

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | FastAPI + Python 3.14 |
| ORM | SQLAlchemy (async) + psycopg3 |
| Database | PostgreSQL 17 |
| Frontend | Jinja2 templates + TypeScript + Tailwind CSS 4 |
| Build | Vite 6 (com manifest para cache busting) |
| Package Manager | uv |

## Estrutura do Projeto

```
app/
├── main.py          # FastAPI app, lifespan, middlewares, static mount
├── config.py        # Pydantic Settings (env vars)
├── db.py            # Engine, session factory, Base
├── auth.py          # Cookie session (itsdangerous)
├── assets.py        # Vite manifest reader
├── models/
│   ├── bet.py       # Bet model (BetType, BetResult, BetMarket enums)
│   └── settings.py  # AppSettings key-value
├── schemas/
│   └── bet.py       # Pydantic schemas (BetCreate, BetResultUpdate)
├── services/
│   └── bets.py      # Business logic (create, update, resolve, delete, list)
├── routes/
│   ├── views.py     # HTML pages (home, login, dashboard, settings)
│   ├── bets.py      # API CRUD (/bets)
│   └── stats.py     # API stats (/stats)
└── templates/       # Jinja2 HTML templates

frontend/
├── src/
│   ├── main.ts      # Entry point, page router
│   ├── home.ts      # Modal, form submit, result buttons
│   ├── dashboard.ts # Chart.js dashboard
│   └── style.css    # Tailwind + custom CSS
├── vite.config.ts
└── tailwind.config.js

static/
├── dist/            # Build output (versionado, hashes no nome)
├── logo.svg
└── favicon.svg
```

## Banco de Dados

Schema: `bet_tracker`

### Tabela `bets`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID (pk) | uuid7 (ordenável temporalmente) |
| created_at | TIMESTAMPTZ | server_default now() |
| bet_date | DATE | data da aposta |
| game_name | TEXT | nome do jogo (nullable) |
| bet_type | VARCHAR | "principal" ou "zoiao" |
| market | TEXT | mercado (over_X_X, asiatico_X_X) |
| stake | NUMERIC(10,2) | valor apostado |
| odd | NUMERIC(6,3) | odd |
| result | VARCHAR | "green", "red", "void" (nullable = pendente) |
| return_amount | NUMERIC(10,2) | retorno calculado |
| group_id | UUID | agrupa principal+zoião do mesmo jogo |
| notes | TEXT | não usado no front, mantido no schema |

### Tabela `app_settings`

Key-value para configurações do app (banca_inicial, stakes padrão, etc).

## Autenticação

- Middleware `AuthMiddleware` (BaseHTTPMiddleware)
- Cookie `session` assinado com `itsdangerous.URLSafeSerializer`
- Paths excluídos: `/login`, `/health`, `/static/*`

## Frontend Build

- Vite gera assets com hash no nome (cache busting)
- Manifest em `static/dist/.vite/manifest.json`
- `assets.py` lê o manifest e expõe `vite_asset()` como global Jinja (`{{ vite.js }}`, `{{ vite.css }}`)

## Desenvolvimento Local

```bash
# Subir banco
make db-up

# Rodar app (builda front + fastapi dev)
make dev

# Apenas rebuild frontend
make frontend-build

# Testes
make test
```

### Variáveis de Ambiente (.env)

```
DATABASE_URL=postgresql+psycopg://bet:bet@localhost:5432/bet_tracker
APP_PASSWORD=troque_isso
SESSION_SECRET=gere_uma_chave_aleatoria_longa
TIMEZONE=America/Sao_Paulo
```

## Deploy (FastAPI Cloud)

- Assets estáticos versionados no repo (static/dist/)
- `DATABASE_URL` aponta para banco remoto
- Normalização automática de URL (`postgres://` → `postgresql+psycopg://`)
- Startup: cria schema + tabelas + migrations inline (ALTER TABLE ADD COLUMN IF NOT EXISTS)

## Testes

- pytest + httpx AsyncClient
- SQLite in-memory para testes (schema removido)
- Fixture `client` já autenticada via cookie
