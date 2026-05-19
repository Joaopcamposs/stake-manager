import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from assets import vite_asset
from config import settings
from db import Base, engine
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeSerializer
from routes import router
from starlette.middleware.base import BaseHTTPMiddleware

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
PROJECT_ROOT = BASE_DIR.parent
STATIC_DIR = PROJECT_ROOT / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    import logging

    from sqlalchemy import text

    logger = logging.getLogger(__name__)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS bet_tracker"))
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(
                text("ALTER TABLE bet_tracker.bets ADD COLUMN IF NOT EXISTS market TEXT")
            )
        logger.info("Schema bet_tracker + tables created")
    except Exception as e:
        logger.warning("Could not connect to database on startup: %s", e)
    yield
    await engine.dispose()


app = FastAPI(title="Bet Tracker", lifespan=lifespan)

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["vite"] = vite_asset("src/main.ts")

# Static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Session / Auth Middleware ---

serializer = URLSafeSerializer(settings.session_secret)

EXCLUDED_PATHS = {"/login", "/health"}
EXCLUDED_PREFIXES = ("/static/", "/favicon")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in EXCLUDED_PATHS or any(path.startswith(p) for p in EXCLUDED_PREFIXES):
            return await call_next(request)

        session_cookie = request.cookies.get("session")
        if session_cookie:
            try:
                data = serializer.loads(session_cookie)
                if data.get("authenticated"):
                    request.state.authenticated = True
                    return await call_next(request)
            except Exception:
                pass

        if request.method == "GET":
            return RedirectResponse(url="/login", status_code=302)
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})


app.add_middleware(AuthMiddleware)


# --- Routes ---

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
