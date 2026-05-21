from datetime import date
from decimal import Decimal
from pathlib import Path

from assets import vite_asset
from auth import clear_session_cookie, create_session_cookie
from config import settings
from db import get_db
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from models.settings import AppSettings
from services import bets as bet_service
from sqlalchemy.ext.asyncio import AsyncSession
from utils import SAO_PAULO_TZ, today_sp

router = APIRouter()
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
templates.env.globals["vite"] = vite_asset("src/main.ts")


def _sp_dt(dt, fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Convert a datetime to São Paulo timezone and format it."""
    if dt is None:
        return ""
    return dt.astimezone(SAO_PAULO_TZ).strftime(fmt)


templates.env.filters["sp_dt"] = _sp_dt


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    session: AsyncSession = Depends(get_db),
    day: str | None = None,
):
    today = today_sp()
    selected_date = date.fromisoformat(day) if day else today

    pending = await bet_service.list_pending(session)
    resolved_day = await bet_service.list_resolved(
        session, date_from=selected_date, date_to=selected_date, limit=100
    )
    day_pending = [b for b in pending if b.bet_date.astimezone(SAO_PAULO_TZ).date() == selected_date]

    greens_day = sum(1 for b in resolved_day if b.result and b.result.value == "green")
    reds_day = sum(1 for b in resolved_day if b.result and b.result.value == "red")
    lucro_day = sum((b.return_amount or Decimal("0")) - b.stake for b in resolved_day)

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "pending": day_pending,
            "resolved": resolved_day,
            "selected_date": selected_date.isoformat(),
            "is_today": selected_date == today,
            "apostas_hoje": len(day_pending) + len(resolved_day),
            "greens_today": greens_day,
            "reds_today": reds_day,
            "lucro_hoje": lucro_day,
        },
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == settings.app_password:
        response = RedirectResponse(url="/", status_code=303)
        return create_session_cookie(response)
    return templates.TemplateResponse(
        request, "login.html", {"error": "Senha incorreta"}, status_code=401
    )


@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    return clear_session_cookie(response)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, session: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    stmt = select(AppSettings)
    result = await session.execute(stmt)
    all_settings = {s.key: s.value for s in result.scalars().all()}
    return templates.TemplateResponse(request, "settings.html", {"settings": all_settings})


@router.post("/settings")
async def update_settings(
    request: Request,
    session: AsyncSession = Depends(get_db),
    banca_inicial: str = Form("1000"),
    stake_principal_default: str = Form("100"),
    stake_zoiao_default: str = Form("25"),
    odd_minima: str = Form("1.5"),
):
    items = {
        "banca_inicial": banca_inicial,
        "stake_principal_default": stake_principal_default,
        "stake_zoiao_default": stake_zoiao_default,
        "odd_minima": odd_minima,
    }
    for key, value in items.items():
        existing = await session.get(AppSettings, key)
        if existing:
            existing.value = value
        else:
            session.add(AppSettings(key=key, value=value))
    await session.commit()
    return RedirectResponse(url="/settings", status_code=302)
