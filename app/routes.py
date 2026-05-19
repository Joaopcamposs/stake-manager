"""Rotas API — endpoints de negócio."""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from infra.config import settings
from infra.database import get_session
from telegram import client as tg_client
from telegram.service import edit_by_reference, list_pending, send_and_store

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/bot-info")
async def api_bot_info() -> dict[str, Any]:
    """Diagnóstico: info do bot e status do webhook."""
    me = await tg_client.api_call("getMe")
    webhook = await tg_client.api_call("getWebhookInfo")
    return {
        "polling_mode": settings.telegram_polling,
        "bot": me.get("result", {}),
        "webhook": webhook.get("result", {}),
    }


@router.post("/bot-webhook")
async def api_set_webhook(url: str) -> dict[str, Any]:
    """Registra webhook no Telegram. url = URL pública completa do app."""
    webhook_url = f"{url.rstrip('/')}{settings.webhook_path}"
    params: dict[str, Any] = {"url": webhook_url}
    if settings.telegram_webhook_secret:
        params["secret_token"] = settings.telegram_webhook_secret
    result = await tg_client.api_call("setWebhook", **params)
    return {"webhook_url": webhook_url, "result": result.get("result")}


@router.post("/send")
async def api_send(
    text: str,
    reference_key: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Envia mensagem ao canal configurado."""
    record = await send_and_store(
        session,
        settings.telegram_channel_id,
        text,
        reference_key=reference_key,
    )
    return {
        "message_id": record.message_id,
        "reference_key": record.reference_key,
        "status": record.status,
    }


@router.get("/pending")
async def api_pending(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Lista mensagens pendentes de atualização."""
    records = await list_pending(session)
    return [
        {
            "id": r.id,
            "chat_id": r.chat_id,
            "message_id": r.message_id,
            "reference_key": r.reference_key,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.put("/edit")
async def api_edit(
    reference_key: str,
    text: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Edita mensagem por reference_key."""
    result = await edit_by_reference(session, reference_key, text)
    if not result:
        raise HTTPException(404, "Message not found")
    return {"status": "edited"}


@router.post("/demo")
async def api_demo(
    initial_text: str = "⏳ Carregando dados...",
    final_text: str = "✅ Dados carregados com sucesso!",
    delay: int = 3,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Demo: envia mensagem, espera N segundos e edita. Fluxo completo de scraping."""
    import uuid

    ref_key = f"demo-{uuid.uuid7()}"

    record = await send_and_store(
        session,
        settings.telegram_channel_id,
        initial_text,
        reference_key=ref_key,
    )

    await asyncio.sleep(min(delay, 10))

    result = await edit_by_reference(session, ref_key, final_text)

    return {
        "reference_key": ref_key,
        "message_id": record.message_id,
        "initial_text": initial_text,
        "final_text": final_text,
        "delay": delay,
        "status": "done" if result else "error",
    }
