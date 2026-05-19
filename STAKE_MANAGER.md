# Bet Tracker — Planejamento de Desenvolvimento

## Visão Geral

Web-app single-user para registro rápido de apostas esportivas com dashboard de
performance. Foco em **velocidade de cadastro pelo celular** (10 segundos por
aposta) e **visualização clara** de métricas de longo prazo (taxa de acerto, ROI,
edge sobre breakeven).

## Stack Técnica

- **Backend**: Python 3.14+, FastAPI
- **ORM**: SQLAlchemy 2.0 (sintaxe nova, `Mapped`/`mapped_column`)
- **Banco**: PostgreSQL 17
- **Migrations**: Alembic - desnecessario agora
- **Tooling**: `uv` (deps), `ruff` (lint/format), `ty` (type check)
- **Frontend**: TypeScript vanilla compilado, HTML renderizado no backend via
  Jinja2. Sem framework JS pesado. CSS simples (pode usar Pico.css ou similar
  para evitar reinventar a roda).
- **Charts**: Chart.js (CDN) — suficiente e leve.
- **Infra local**: Docker Compose (app + postgres + adminer opcional).
- App deve ser limitado a 256mb de memoria. Backend hospedado no fastapi cloud.

## Autenticação

Single-user com **senha simples**:
- Variável `APP_PASSWORD` no `.env`.
- Login via form POST, cookie de sessão HTTP-only assinado.
- Middleware verifica sessão em todas as rotas exceto `/login`, `/static/*`,
  `/health`.
- Sem registro de usuário, sem recuperação de senha. Mantém simples.

## Modelo de Dados

### Tabela `bets`

| Campo            | Tipo            | Notas                                        |
|------------------|-----------------|----------------------------------------------|
| `id`             | UUID7 PK        | Use `uuid7` lib (UUID7 ordena temporalmente) |
| `created_at`     | timestamptz     | `default=now()`                              |
| `bet_date`       | date            | Data da aposta (não do registro)             |
| `game_name`      | text NULL       | Opcional                                     |
| `bet_type`       | enum            | `principal`, `zoiao`                         |
| `stake`          | numeric(10,2)   | Valor apostado                               |
| `odd`            | numeric(6,3)    | Odd no momento da aposta                     |
| `result`         | enum NULL       | `green`, `red`, `void`, NULL (pendente)      |
| `return_amount`  | numeric(10,2)   | Calculado, mas armazenado pra histórico      |
| `group_id`       | UUID NULL       | Liga principal + zoião do mesmo jogo         |
| `notes`          | text NULL       | Observações                                  |

**Sobre `group_id`**: quando o cadastro vier do modal duplo (principal + zoião
no mesmo jogo), as duas linhas recebem o mesmo `group_id` (gerado no backend).
Quando só uma é cadastrada, `group_id` fica null. Permite agrupar visualmente e
calcular EV combinado depois.

**Cálculo de `return_amount`** (no backend, ao definir o resultado):
- `green` → `stake * odd`
- `red` → `0`
- `void` → `stake`
- `null` (pendente) → `null`

**Lucro/prejuízo** é sempre `return_amount - stake` (calculado em queries, não
armazenado).

### Tabela `settings` (chave-valor)

Para parâmetros editáveis sem deploy: banca inicial, stake padrão principal,
stake padrão zoião, odd mínima de corte, etc. Schema simples:

| Campo   | Tipo | Notas             |
|---------|------|-------------------|
| `key`   | text | PK                |
| `value` | text | serializado JSON  |

Seed inicial:
```python
{
  "banca_inicial": 1000,
  "stake_principal_default": 100,
  "stake_zoiao_default": 25,
  "odd_minima": 1.5,
}
```

## Cadastro de Apostas (UX Crítica)

### Tela principal: botão grande "Nova aposta" → abre modal.

### Modal de cadastro

Layout vertical, otimizado pra mobile:

```
┌──────────────────────────────┐
│ Nova Aposta              [X] │
├──────────────────────────────┤
│ Jogo (opcional)              │
│ [____________________]       │
│                              │
│ Data                         │
│ [hoje ▼]                     │
│                              │
│ ┌─ Principal ────────────┐   │
│ │ Valor:  [R$ 100   ]    │   │
│ │ Odd:    [_______ ]     │   │
│ └────────────────────────┘   │
│                              │
│ ┌─ Zoião ────────────────┐   │
│ │ Valor:  [R$ 25    ]    │   │
│ │ Odd:    [_______ ]     │   │
│ └────────────────────────┘   │
│                              │
│ Retorno potencial:           │
│ Principal: R$ ---            │
│ Zoião:     R$ ---            │
│                              │
│       [Salvar]               │
└──────────────────────────────┘
```

**Regras**:
- `jogo` e `data` são compartilhados (preenchidos uma vez).
- `data` pré-preenchida com hoje.
- Bloco Principal: valor padrão **R$ 100**, odd vazia.
- Bloco Zoião: valor padrão **R$ 25**, odd vazia.
- **Cada bloco é independente e opcional**. Se odd estiver vazia, aquele bloco
  não é cadastrado.
- Pelo menos um dos blocos precisa estar preenchido (validação no submit).
- "Retorno potencial" é calculado em tempo real no frontend (TS vanilla) assim
  que o usuário digita a odd: `valor * odd`.
- Ao salvar com os dois blocos preenchidos: cria duas linhas no banco com o
  mesmo `group_id`.
- Resultado **não** é preenchido no cadastro — fica pendente.

### Atualização de resultado

Lista de apostas pendentes na home, cada uma com três botões grandes:
**[GREEN] [RED] [VOID]**. Um clique resolve a aposta e atualiza KPIs ao vivo.

Apostas resolvidas vão pra uma tabela secundária (histórico), filtrável por
data.

## Endpoints da API

```
GET  /                          → home (lista pendentes + KPIs do dia)
GET  /login                     → form
POST /login                     → autentica
POST /logout

GET  /bets                      → lista paginada com filtros (data, tipo, result)
POST /bets                      → cria 1 ou 2 bets (modal duplo)
PATCH /bets/{id}/result         → seta resultado e calcula return_amount
DELETE /bets/{id}               → remove (cuidado: ajustar group)

GET  /dashboard                 → página com gráficos
GET  /api/stats                 → JSON com KPIs (consumido por Chart.js)
GET  /api/stats/timeseries      → JSON com banca ao longo do tempo

GET  /settings                  → página de configuração
POST /settings                  → atualiza valores
```

## Dashboard

Mínimo viável = paridade com a planilha. Bom = superior.

### KPIs (cards no topo)

- Banca atual (banca inicial + soma de lucros)
- Variação % sobre banca inicial
- Total apostado
- Lucro/prejuízo líquido
- ROI geral
- Taxa de acerto (greens / (greens+reds), ignorando voids e pendentes)
- Odd média ponderada por stake
- Breakeven necessário (1 / odd média)
- **Edge** (taxa real - breakeven) — KPI mais importante; pinta verde se
  positivo, vermelho se negativo

### Gráficos

1. **Banca ao longo do tempo** (line chart) — eixo X data, eixo Y banca. Linha
   horizontal tracejada na banca inicial.
2. **Lucro acumulado por tipo** (line chart, duas séries) — separar curva da
   principal e do zoião. Crítico pra saber qual estratégia está performando.
3. **Distribuição de odds** (histograma) — bins de 0.1 entre 1.0 e 3.0. Ajuda
   a ver se o usuário está respeitando o corte de 1.5.
4. **Taxa de acerto por faixa de odd** (bar chart) — odds 1.5-1.6, 1.6-1.7,
   etc. Mostra em qual faixa o tipster acerta mais.
5. **Resultado por dia da semana** (bar chart) — útil pra identificar padrões.
6. **Heatmap mensal** — calendário com cor por lucro diário (estilo GitHub
   contributions). Visual e motivacional.

### Diferenciais sobre a planilha

- **Filtros interativos**: período (7d, 30d, 90d, tudo), tipo (principal/zoião/
  ambos).
- **Comparação real vs esperado**: cartão mostrando o EV teórico baseado em
  taxa histórica vs o lucro real, com gap.
- **Streak atual**: "5 greens seguidos" ou "2 reds seguidos".
- **Drawdown máximo**: maior queda da banca já registrada (útil pra dimensionar
  banca futura).
- **Projeção de banca em 30/90/365 dias** baseada no ROI real dos últimos 30
  dias. Banner discreto, deixar claro que é projeção, não promessa.

## Estrutura do Projeto

```
bet-tracker/
├── pyproject.toml          # uv, ruff, ty configurados
├── docker-compose.yml      # app + postgres
├── Dockerfile
├── .env.example
├── alembic.ini
├── migrations/
├── src/
│       ├── __init__.py
│       ├── main.py         # FastAPI app + middleware
│       ├── config.py       # pydantic-settings
│       ├── auth.py         # senha + sessão
│       ├── db.py           # engine, session
│       ├── models/
│       │   ├── bet.py
│       │   └── settings.py
│       ├── schemas/        # Pydantic
│       ├── routes/
│       │   ├── bets.py
│       │   ├── stats.py
│       │   └── views.py    # rotas que renderizam HTML
│       ├── services/
│       │   ├── stats.py    # cálculos de KPI
│       │   └── bets.py
│       └── templates/
│           ├── base.html
│           ├── login.html
│           ├── home.html
│           └── dashboard.html
├── static/
│   ├── css/
│   ├── js/                 # TS compilado
│   └── src/                # TS fonte
└── tests/
    ├── test_bets.py
    ├── test_stats.py
    └── conftest.py
```

## Princípios de Implementação

### Domain-Driven (leve)
- Lógica de cálculo de KPIs em `services/stats.py`, não nas rotas.
- Schemas Pydantic separados dos modelos SQLAlchemy.
- Routes finas: validação → service → response.

### Type safety
- `ty` rodando em CI. Sem `Any` exceto onde inevitável.
- Mapped columns com tipos explícitos.

### Testes
- Pytest + factory-boy ou fixtures simples.
- Cobertura mínima: cálculos de KPI (stats service), criação de bets com
  group_id, atualização de resultado.
- Use uma DB de teste separada (sqlite em memória OU postgres docker no CI).

### Frontend TS
- Sem bundler pesado. Use `esbuild` ou `tsc` simples gerando um JS por página.
- Funcionalidades:
  - Cálculo de retorno potencial no modal (reativo).
  - Validação do form antes do submit.
  - Confirmação ao clicar Green/Red/Void.
  - Renderização dos gráficos com Chart.js (importado via CDN no template).

## Roadmap de Desenvolvimento

Sugestão de ordem (cada item é um commit ou PR pequeno):

1. **Setup**: pyproject, docker-compose, .env, alembic init, ruff/ty rodando.
2. **Modelos + migration inicial**: `bets`, `settings`.
3. **Auth**: middleware de senha, login/logout, templates base.
4. **CRUD de bets** (API + testes): criar (single e double), listar, resolver,
   deletar.
5. **Home**: lista de pendentes + botões de resolução.
6. **Modal de cadastro** (frontend TS).
7. **Service de stats** com testes extensivos — esse é o coração.
8. **Dashboard**: KPIs + 2 gráficos principais (banca, lucro por tipo).
9. **Gráficos avançados**: distribuição, taxa por faixa, heatmap.
10. **Settings page**: editar banca, stakes default.
11. **Polish**: filtros, dark mode, PWA manifest para "instalar" no celular.

## Detalhes para Não Esquecer

- **Timezone**: armazenar tudo em UTC, exibir em America/Sao_Paulo.
- **Decimal**: usar `decimal.Decimal` no Python para money, nunca float. Mapear
  pra `numeric(10,2)` no Postgres.
- **CSRF**: implementar token CSRF nos forms (FastAPI não tem built-in; pode
  usar `starlette-csrf` ou um middleware simples).
- **Rate limit no login**: pra senha simples não ser bruteforceável (slowapi).
- **Backup**: comando `make backup` que faz `pg_dump` num volume montado. Vai
  ser triste perder histórico.
- **Seeds**: comando que popula settings iniciais ao subir pela primeira vez.
- **Idempotência**: criar bet com o mesmo conjunto de campos em curto intervalo
  deve avisar (provável duplo-clique).

## Arquivo `.env.example`

```
DATABASE_URL=postgresql+psycopg://bet:bet@db:5432/bet_tracker
APP_PASSWORD=troque_isso
SESSION_SECRET=gere_uma_chave_aleatoria_longa
TIMEZONE=America/Sao_Paulo
```

## Critérios de Aceite (MVP)

- Login com senha funciona.
- Cadastro modal duplo cria 1 ou 2 bets corretamente.
- Resolver aposta atualiza KPIs imediatamente.
- Dashboard mostra todos os KPIs da planilha + os gráficos 1, 2 e 3.
- `ruff check` e `ty check` passam sem erro.
- Testes do service de stats verdes.
- `docker compose up` sobe tudo do zero (incluindo migrations).