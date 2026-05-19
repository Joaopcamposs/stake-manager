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
│   ├── bet.py       # Pydantic schemas (BetCreate, BetResultUpdate)
│   └── stats.py     # KPIResponse, TimeseriesPoint, ProfitByTypePoint, etc
├── services/
│   ├── bets.py      # Business logic (create, update, resolve, delete, list)
│   └── stats.py     # KPIs, timeseries, distribuição odds, hit rate, weekday
├── routes/
│   ├── views.py     # HTML pages (home, login, dashboard, settings)
│   ├── bets.py      # API CRUD (/bets)
│   └── stats.py     # API stats (/api/stats/*)
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
| market | TEXT | mercado (over_X_5, asiatico_N) |
| stake | NUMERIC(10,2) | valor apostado |
| odd | NUMERIC(6,3) | odd |
| result | VARCHAR | "green", "red", "void" (nullable = pendente) |
| return_amount | NUMERIC(10,2) | retorno calculado |
| group_id | UUID | agrupa principal+zoião do mesmo jogo |
| notes | TEXT | não usado no front, mantido no schema |

### Tabela `app_settings`

Key-value para configurações do app (banca_inicial, stakes padrão, etc).

## API — Stats Endpoints

Prefixo: `/api/stats`. Todos aceitam query params `period` (7d|30d|90d|all) e `bet_type` (principal|zoiao).

| Endpoint | Retorno |
|----------|---------|
| `GET /api/stats` | KPIs: banca_atual, banca_inicial, variacao_pct, total_apostado, lucro_liquido, roi, taxa_acerto, odd_media_ponderada, breakeven, edge, streak_atual, streak_tipo, drawdown_maximo, total_apostas, stake_medio |
| `GET /api/stats/timeseries` | Array de {date, banca} — evolução diária da banca |
| `GET /api/stats/profit-by-type` | Array de {date, principal, zoiao} — lucro acumulado por tipo |
| `GET /api/stats/odds-distribution` | Array de {range_start, range_end, count} — histograma de odds (step 0.1) |
| `GET /api/stats/hit-rate-by-odds` | Array de {range_label, total, greens, rate} — taxa acerto por faixa |
| `GET /api/stats/weekday` | Array de {weekday, weekday_name, profit, count} — lucro por dia da semana |
| `GET /api/stats/market-profit` | Array de {market, profit, count, rate} — lucro e taxa por mercado |
| `GET /api/stats/monthly` | Array de {month, profit, count} — lucro mensal agregado |

### Lógica de Cálculo (stats service)

- Filtra apenas apostas resolvidas (result != null), exclui void dos totais
- **Banca atual** = banca_inicial + lucro_liquido
- **ROI** = lucro / total apostado × 100
- **Odd média** = ponderada por stake (Σ(odd×stake) / Σstake)
- **Breakeven** = 1 / odd_média × 100
- **Edge** = taxa_acerto - breakeven (positivo = vantagem)
- **Drawdown** = maior queda entre pico e vale na evolução da banca
- **Streak** = sequência final de resultados iguais (green ou red)

## Autenticação

- Middleware `AuthMiddleware` (BaseHTTPMiddleware)
- Cookie `session` assinado com `itsdangerous.URLSafeSerializer`
- Paths excluídos: `/login`, `/health`, `/static/*`, `/favicon*`

## Frontend — Dashboard (dashboard.ts)

- Chart.js com registro modular (LineController, BarController, scales, plugins)
- Dark theme defaults (color #ccc, borderColor #333)
- 5 gráficos independentes, cada um busca seu endpoint e faz destroy/recreate no refresh
- Filtros (period + bet_type) disparam `loadAll()` que recarrega KPIs + todos os gráficos em paralelo
- Gráfico de banca inclui linha tracejada referência (banca inicial hardcoded 1000 — TODO: buscar do settings)
- Cores: azul (#2196f3) principal, laranja (#ff9800) zoião, verde/vermelho conforme lucro

## Frontend — Home (home.ts)

- Modal `<dialog>` reutilizado pra criar e editar
- Modo criação: mostra principal + zoião, resultado opcional
- Modo edição: esconde fieldset oposto, preenche valores, mostra botão excluir
- Result buttons: visual feedback com ring-2 ring-white na seleção
- Cálculo retorno em tempo real (stake × odd normalizada)
- Delete com confirm() nativo

## Frontend — Odd Input

- Campo `type="text" inputmode="decimal"` (teclado numérico no mobile)
- Auto-conversão no submit: "155" → "1.55" (ponto após primeiro dígito)
- Cálculo de retorno usa normalização em tempo real

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
