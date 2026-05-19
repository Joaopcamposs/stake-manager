# Architecture — FastAPI Telegram Base

## Visão Geral

App minimalista para **scraping web + envio/edição de mensagens Telegram**.
Combina FastAPI (HTTP/API) com Telegram Bot (polling/webhook) e scheduler para rotinas periódicas.
Projetado para rodar em **256MB RAM**, sem autenticação.

```
┌───────────────────────────────────────────────────────────┐
│                       FastAPI App                          │
│                                                            │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐       │
│  │ /health  │  │ /api/*   │  │ /webhook/telegram  │       │
│  └──────────┘  └────┬─────┘  └────────┬───────────┘       │
│                     │                 │                    │
│              ┌──────▼─────────────────▼────────────┐      │
│              │       telegram/service.py           │      │
│              │  envio + persistência + status      │      │
│              └──────┬─────────────────┬────────────┘      │
│                     │                 │                    │
│  ┌──────────┐┌──────▼──────┐   ┌──────▼────────────┐     │
│  │scheduler ││ client.py   │   │  models.py        │     │
│  │  + jobs  ││ (httpx)     │   │ (SentMessage)     │     │
│  └────┬─────┘└──────┬──────┘   └──────┬────────────┘     │
│       │             │                 │                    │
└───────┼─────────────┼─────────────────┼────────────────────┘
        │             │                 │
        │     ┌───────▼──┐       ┌──────▼─────┐
        └────►│ Telegram  │       │ PostgreSQL │
              │ Bot API   │       │  :54310    │
              └───────────┘       └────────────┘
```

## Estrutura de Arquivos

```
app/
  main.py                  → Entry point, lifespan, webhook
  routes.py                → APIRouter com endpoints de negócio (/api/*)
  scheduler.py             → Scheduler para rotinas periódicas
  infra/
    config.py              → Settings via pydantic-settings (.env)
    database.py            → Engine async + session factory (SSL, pool strategy)
    models.py              → Base entity + SentMessage (UUID7, status, schema)
  telegram/
    client.py              → Cliente HTTP (httpx) → Telegram API (retry + HTML)
    handler.py             → Processa updates (polling ou webhook)
    polling.py             → Long polling para dev local
    service.py             → Envio/edição com persistência e status
  jobs/
    __init__.py            → Registro de todos os jobs
    example.py             → Job modelo (heartbeat a cada 5 min)
tests/                     → Testes unitários (90%+ coverage, SQLite em memória)
scripts/
  setup.sh                 → Setup automático (bot + banco + validação)
  validate.sh              → Validação envio/edição com dados mock
Dockerfile                 → Multi-stage build otimizado (uvloop, --no-access-log)
docker-compose.yml         → App :8010 + Postgres :54310 (256MB limit)
Makefile                   → Comandos dev/prod/setup/validate
```

## Portas

| Serviço | Porta externa | Porta interna |
|---------|---------------|---------------|
| FastAPI | 8010          | 8000 |
| PostgreSQL | 54310      | 5432 |

Portas não-padrão para evitar conflito com outros serviços locais.

## PYTHONPATH

O projeto usa `PYTHONPATH=app` para que imports como `from infra.config` e `from telegram.client` funcionem.
Já configurado em: Makefile, Dockerfile, pytest.ini e scripts.

Imports internos usam path sem prefixo `app.`:
```python
from telegram import client       # não "from app.telegram"
from infra.config import settings  # não "from app.infra.config"
from scheduler import register     # não "from app.scheduler"
```

---

## Fluxo de Scraping → Telegram

Fluxo principal do app. Scraper coleta dados, envia mensagem "carregando" e depois edita com resultado.

### Passo a passo

```
1. Scraper inicia
   └→ send_and_store(chat_id, "⏳ Carregando...", reference_key="btc-daily")
   └→ Telegram recebe mensagem
   └→ SentMessage salvo: status="pending", id=UUID7

2. Scraping executa (segundos a minutos)
   └→ httpx busca dados de sites
   └→ Processa/formata resultado

3. Scraper finaliza com sucesso
   └→ edit_by_reference("btc-daily", "📊 BTC: $104.250 ...")
   └→ Telegram edita mensagem existente
   └→ SentMessage atualizado: status="done"

4. Ou scraper falha
   └→ mark_error("btc-daily", "timeout na API")
   └→ SentMessage atualizado: status="error", error_detail="timeout na API"
```

### Em código

```python
from infra.database import async_session
from telegram.service import send_and_store, edit_by_reference, mark_error


async def scrape_and_notify(chat_id: int):
    async with async_session() as session:
        await send_and_store(
            session, chat_id,
            "⏳ Cotação BTC — carregando...",
            reference_key="btc-daily",
        )

    try:
        data = await fetch_btc_price()
    except Exception as e:
        async with async_session() as session:
            await mark_error(session, "btc-daily", str(e))
        return

    async with async_session() as session:
        await edit_by_reference(
            session, "btc-daily",
            f"📊 BTC: ${data['price']:,.2f}\n📈 24h: {data['change']}%",
        )
```

### Ciclo de status

```
send_and_store()     →  status = "pending"   (mensagem enviada, aguardando dados)
edit_by_reference()  →  status = "done"      (mensagem editada com dados finais)
mark_error()         →  status = "error"     (falha, com error_detail)
```

Consultar pendentes: `GET /api/pending` ou `await list_pending(session)`.

### Formatação HTML

Mensagens usam `parse_mode=HTML` por padrão. Formatar texto com:

```python
text = "<b>BTC</b>: $104.250\n<i>+2.3% 24h</i>\n<a href='https://...'>fonte</a>"
await client.send_message(chat_id, text)
```

Tags suportadas: `<b>`, `<i>`, `<u>`, `<s>`, `<code>`, `<pre>`, `<a href>`.

### Via endpoints HTTP

```bash
# Envia placeholder (retorna id UUID7 + message_id + status=pending)
curl -X POST "http://localhost:8010/api/send?text=⏳+Carregando...&reference_key=btc-daily"

# Edita com dados finais (status → done)
curl -X PUT "http://localhost:8010/api/edit?reference_key=btc-daily&text=📊+BTC:+$104.250"

# Lista mensagens pendentes
curl "http://localhost:8010/api/pending"

# Demo end-to-end (envia + espera + edita)
curl -X POST "http://localhost:8010/api/demo?delay=2"
```

### Validação rápida

```bash
make validate   # envia 2 mensagens mock (BTC + ETH) e edita após 2s
```

---

## Endpoints de Diagnóstico

Endpoints para verificar status do bot e configurar webhook sem curl manual.

```bash
# Info do bot + status do webhook/polling
curl http://localhost:8010/api/bot-info

# Registrar webhook (produção)
curl -X POST "http://localhost:8010/api/bot-webhook?url=https://meuapp.com"
```

`/api/bot-info` retorna: modo polling/webhook, dados do bot (@username), e status do webhook atual.

`/api/bot-webhook` registra webhook no Telegram apontando para `{url}/webhook/telegram`, incluindo secret se configurado.

---

## Scheduler (Rotinas Periódicas)

Scheduler interno baseado em asyncio — sem dependências externas (sem celery, sem APScheduler).
Inicia no lifespan, cancela no shutdown. Se um job falha, loga o erro e continua no próximo ciclo.

Jobs têm delay inicial antes da primeira execução (evita race condition com banco/Telegram no startup).

### Como funciona

```python
# scheduler.py
@register("nome-do-job", interval_seconds=300)
async def meu_job():
    ...
```

O decorator `@register` adiciona o job à lista. `start_all()` no lifespan cria uma `asyncio.Task` por job. `stop_all()` cancela tudo no shutdown.

### Criar novo job

1. Crie arquivo em `app/jobs/`:

```python
# app/jobs/crypto_scraper.py
import httpx

from scheduler import register
from telegram.service import send_and_store, edit_by_reference, mark_error
from infra.config import settings
from infra.database import async_session


@register("crypto-scraper", interval_seconds=300)
async def scrape_crypto():
    ref_key = "btc-latest"

    async with async_session() as session:
        await send_and_store(
            session, settings.telegram_channel_id,
            "⏳ Atualizando BTC...",
            reference_key=ref_key,
        )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.example.com/btc")
            data = resp.json()
    except Exception as e:
        async with async_session() as session:
            await mark_error(session, ref_key, str(e))
        return

    async with async_session() as session:
        await edit_by_reference(
            session, ref_key,
            f"<b>BTC</b>: ${data['price']:,.2f}\n📈 {data['change']}%",
        )
```

2. Registre no `app/jobs/__init__.py`:

```python
from jobs import example, crypto_scraper  # noqa: F401
```

Pronto — roda automaticamente a cada 5 minutos.

### Job existente (exemplo)

`app/jobs/example.py` — heartbeat que loga a cada 5 min. Substitua ou delete.

---

## Polling vs Webhook

O bot suporta dois modos de receber updates do Telegram, controlado por `TELEGRAM_POLLING` no `.env`.

### Polling (padrão, dev local)

```
TELEGRAM_POLLING=true
```

Bot busca updates ativamente via long polling (`getUpdates`). Não precisa de URL pública, ngrok ou túnel. Ideal para desenvolvimento local.

```
App inicia
  └→ delete_webhook()          (limpa webhook anterior)
  └→ loop: getUpdates(timeout=30)
       └→ handle_update() para cada update
       └→ offset avança (não reprocessa)
```

O polling roda como `asyncio.Task` dentro do lifespan — não bloqueia o FastAPI. Se falhar, loga o erro, espera 3s e reconecta.

O client HTTP usa `read=60s` timeout (maior que o long polling de 30s) para evitar `ReadTimeout`.

### Webhook (produção)

```
TELEGRAM_POLLING=false
```

Telegram envia updates via POST para `/webhook/telegram`. Requer URL pública com HTTPS.

```bash
# Configurar webhook via endpoint
curl -X POST "http://localhost:8010/api/bot-webhook?url=https://meuapp.com"

# Ou manualmente
curl "https://api.telegram.org/bot<TOKEN>/setWebhook\
  ?url=https://<APP_URL>/webhook/telegram\
  &secret_token=<SECRET>"
```

O `TELEGRAM_WEBHOOK_SECRET` valida cada request via header `X-Telegram-Bot-Api-Secret-Token` (comparação constant-time).

### Quando usar qual

| Modo | Quando usar | `TELEGRAM_POLLING` |
|------|------------|-------------------|
| **Polling** | Dev local, sem URL pública | `true` |
| **Webhook** | Produção, deploy com HTTPS | `false` |

### Logs

Ambos os modos logam cada update recebido:

```
14:32:01 INFO     telegram.handler — Update recebido: chat_id=123 type=private user=joao text='hello'
14:32:01 INFO     telegram.client — Enviando mensagem para chat_id=123
```

---

## Telegram Handler

`app/telegram/handler.py` — processa updates (polling ou webhook, mesmo handler).

Suporta `message` e `channel_post` (canais). Strip automático de `@botname` suffix em grupos.

Comandos implementados:

| Comando | Resposta |
|---------|----------|
| `/start` | "Bot ativo." + lista de comandos |
| `/ping` | "pong" |
| qualquer outro | "Bot operando em modo automático. Comandos: /start /ping" |

Para adicionar comando:

```python
if text.startswith("/cotacao"):
    await client.send_message(chat_id, "<b>BTC</b>: $104.250")
    return
```

---

## Logging

Logging configurável via `LOG_LEVEL` no `.env` (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

```
LOG_LEVEL=INFO      # padrão
LOG_LEVEL=DEBUG     # verbose — inclui payloads de API e queries
```

Cada módulo loga suas ações:

| Módulo | O que loga |
|--------|-----------|
| `main` | Lifespan (banco, schema, polling/webhook, shutdown) |
| `client` | Chamadas API, retry 429, erros 4xx/5xx com body, open/close |
| `handler` | Updates recebidos (chat, user, texto) |
| `service` | Mensagens armazenadas, editadas, erros |
| `scheduler` | Jobs iniciados, falhas |
| `polling` | Loop iniciado, erros de conexão |

Formato: `HH:MM:SS LEVEL    module — mensagem`

Erros da Telegram API são logados com response body completo para debug.

---

## Banco de Dados

SQLAlchemy 2.0 async com asyncpg.

### Pool Strategy

| Ambiente | Pool | Configuração |
|----------|------|-------------|
| Local (`localhost`) | Pooled | `pool_size=5`, `max_overflow=5`, `pool_pre_ping=True` |
| Cloud (Neon, Supabase) | NullPool | Sem pool — serverless precisa de NullPool |

Detecção automática via URL: se contém `localhost`/`127.0.0.1` → pool, senão → NullPool.

### SSL

Conexão SSL ativada automaticamente quando URL contém `sslmode=require`, `sslmode=verify` ou `supabase`.

### Schema Isolation

`DB_SCHEMA` no `.env` isola tabelas em schema PostgreSQL dedicado. Útil para multi-tenant ou organização.

```
DB_SCHEMA=my_app     # tabelas criadas em schema "my_app"
DB_SCHEMA=           # usa schema "public" (padrão)
```

O schema é criado automaticamente no startup (`CREATE SCHEMA IF NOT EXISTS`). Search path configurado via event listener em cada conexão.

### Startup Resiliente

Se banco estiver indisponível no startup, app sobe com warning — tabelas serão criadas na primeira conexão. Permite deploy antes do banco estar ready.

### SentMessage

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID7 (str, PK) | Ordenável por tempo, sem colisão |
| `chat_id` | bigint | ID do canal/chat Telegram |
| `message_id` | bigint | ID da mensagem no Telegram |
| `content_type` | str | `"text"` ou `"photo"` |
| `status` | str | `"pending"` → `"done"` ou `"error"` |
| `error_detail` | str (nullable) | Detalhe do erro quando `status="error"` |
| `reference_key` | str (nullable, indexed) | Chave de negócio para edição |
| `created_at` | datetime (tz) | Timestamp criação |
| `updated_at` | datetime (tz) | Timestamp última atualização |

**TimestampMixin** — `created_at`/`updated_at` automáticos em todas entidades.

Tabelas criadas automaticamente no lifespan. Para produção, migrar para **Alembic**.

---

## Telegram Client

`app/telegram/client.py` — cliente HTTP leve via httpx com:

- **`parse_mode=HTML`** por padrão em `send_message`, `edit_message_text`, `send_photo`
- **Retry automático** em 429 (rate limit) — respeita `retry_after`, até 3 tentativas
- **Log de erros** — respostas 4xx/5xx logadas com body completo antes do raise
- **Singleton** — reutiliza conexões TCP via `httpx.AsyncClient`
- **Timeout** — `10s` connect/write, `60s` read (compatível com long polling)

Funções disponíveis:

| Função | Descrição |
|--------|-----------|
| `send_message(chat_id, text)` | Envia texto |
| `edit_message_text(chat_id, message_id, text)` | Edita texto |
| `send_photo(chat_id, photo, caption)` | Envia foto (URL ou file_id) |
| `edit_message_media(chat_id, message_id, media)` | Edita mídia |
| `api_call(method, **kwargs)` | Chamada genérica |
| `get_updates(offset, timeout)` | Long polling (usado por `polling.py`) |
| `delete_webhook()` | Remove webhook para ativar polling |

---

## Camadas

| Camada | Arquivo | Responsabilidade |
|--------|---------|------------------|
| **HTTP** | `main.py` | Entry point, lifespan, webhook |
| **Routes** | `routes.py` | Endpoints de negócio (APIRouter) |
| **Scheduler** | `scheduler.py` | Registro e execução de jobs periódicos |
| **Jobs** | `jobs/*.py` | Rotinas periódicas (scrapers, notificações) |
| **Service** | `telegram/service.py` | Envio/edição + persistência + status |
| **Client** | `telegram/client.py` | Telegram Bot API (retry 429 + HTML) |
| **Polling** | `telegram/polling.py` | Long polling para dev local |
| **Handler** | `telegram/handler.py` | Processamento de updates recebidos |
| **Model** | `infra/models.py` | Entidades SQLAlchemy 2.0 |
| **Config** | `infra/config.py` | Variáveis de ambiente |
| **Database** | `infra/database.py` | Engine async + session factory |

Dependência flui para baixo: HTTP → Service → Client/Model. Nunca para cima.

---

## Testes

90%+ coverage. Testes rodam isolados — **nunca tocam banco Postgres ou Telegram API**.

- **Banco**: SQLite em memória via `aiosqlite`
- **Telegram**: mock completo via `unittest.mock`
- **Schema**: `DB_SCHEMA=""` forçado nos testes (SQLite não suporta schemas)
- **Segurança extra**: `DATABASE_URL` forçado pra `localhost:1` (porta inválida) no conftest — se algum código vazar da fixture, falha com connection refused

```bash
make test   # pytest -x --tb=short -q --cov=app --cov-report=term-missing
```

---

## Otimizações (256MB)

- **httpx singleton** — reutiliza conexões TCP
- **Pool strategy** — pooled local, NullPool cloud (evita leak em serverless)
- **uvloop** — event loop otimizado em C
- **--no-access-log** — reduz I/O em produção
- **Multi-stage Docker** — imagem final sem build tools
- **expire_on_commit=False** — evita lazy loads desnecessários
- **UUID7** — ordenável por tempo, gerado no app (sem roundtrip ao banco)
- **Startup resiliente** — app sobe mesmo sem banco disponível

---

## Como Expandir

### Adicionar novo scraper como job periódico

Ver seção [Scheduler](#scheduler-rotinas-periódicas) acima.

### Adicionar novo model

Herde `TimestampMixin` + `Base` em `app/infra/models.py`:

```python
class Alert(TimestampMixin, Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid7)
    name: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)
```

### Adicionar novo endpoint

Adicione no `app/routes.py` ou crie novo router:

```python
# app/routes.py (adicionar ao router existente)
@router.get("/alerts")
async def list_alerts(session: AsyncSession = Depends(get_session)):
    ...

# Ou criar novo router em arquivo separado:
# app/routes_alerts.py
from fastapi import APIRouter
router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# Registrar no main.py:
from routes_alerts import router as alerts_router
app.include_router(alerts_router)
```

### Adicionar Alembic (migrações)

```bash
uv add alembic
uv run alembic init alembic
```

Configurar `alembic/env.py` com async engine e `Base.metadata`.

---

## Deploy

### FastAPI Cloud

```bash
# 1. Deploy
make deploy

# 2. Configurar webhook via endpoint
curl -X POST "https://<APP_URL>/api/bot-webhook?url=https://<APP_URL>"
```

Entry point: `app.main:app`. Variáveis de ambiente configuradas no painel.

### Docker (qualquer cloud)

```bash
docker build -t fastapi-telegram-base .
docker run -p 8010:8000 --env-file .env fastapi-telegram-base
```

Compatível com: Railway, Render, Fly.io, Cloud Run, ECS.

### Variáveis necessárias em produção

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHANNEL_ID=...
TELEGRAM_WEBHOOK_SECRET=...
TELEGRAM_POLLING=false
DATABASE_URL=postgresql+asyncpg://...
LOG_LEVEL=INFO
```

---

## Comandos Make

| Comando | Descrição |
|---------|-----------|
| `make install` | Instala dependências via uv |
| `make dev` | Servidor local com reload (:8010) |
| `make run` | Servidor produção local (:8010) |
| `make test` | Testes com coverage |
| `make lint` | Ruff check + ty check (com auto-fix) |
| `make format` | Auto-format com ruff |
| `make setup` | Setup completo (bot + banco + validação) |
| `make validate` | Testa envio/edição com dados mock |
| `make up` | Docker compose up (build + detached) |
| `make down` | Docker compose down |
| `make resetdb` | Destroi banco + recria + restart app |
| `make clean` | Remove volumes e cache |
| `make deploy` | Deploy via FastAPI Cloud |
