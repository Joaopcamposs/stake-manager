from datetime import datetime
from decimal import Decimal
from uuid import UUID

from db import get_db
from fastapi import APIRouter, Depends, Form, Query
from fastapi.responses import RedirectResponse
from schemas.bet import BetCreate, BetResultUpdate
from services import bets as bet_service
from sqlalchemy.ext.asyncio import AsyncSession
from utils import now_sp

router = APIRouter(prefix="/bets", tags=["bets"])

SP_FMT = "%Y-%m-%dT%H:%M"  # datetime-local input format


def _parse_bet_datetime(raw: str) -> datetime | None:
    """Parse a datetime-local string (YYYY-MM-DDTHH:MM) into a SP-aware datetime."""
    if not raw:
        return None
    try:
        from utils import SAO_PAULO_TZ
        naive = datetime.strptime(raw, SP_FMT)
        return naive.replace(tzinfo=SAO_PAULO_TZ)
    except ValueError:
        return None


@router.post("")
async def create_bet(
    session: AsyncSession = Depends(get_db),
    game_name: str = Form(""),
    bet_date: str = Form(""),
    principal_stake: str = Form(""),
    principal_odd: str = Form(""),
    principal_market: str = Form(""),
    principal_result: str = Form(""),
    zoiao_stake: str = Form(""),
    zoiao_odd: str = Form(""),
    zoiao_market: str = Form(""),
    zoiao_result: str = Form(""),
):
    data = BetCreate(
        game_name=game_name or None,
        bet_date=_parse_bet_datetime(bet_date),
        principal_stake=Decimal(principal_stake) if principal_stake else None,
        principal_odd=Decimal(principal_odd) if principal_odd else None,
        principal_market=principal_market or None,
        principal_result=principal_result or None,
        zoiao_stake=Decimal(zoiao_stake) if zoiao_stake else None,
        zoiao_odd=Decimal(zoiao_odd) if zoiao_odd else None,
        zoiao_market=zoiao_market or None,
        zoiao_result=zoiao_result or None,
    )
    await bet_service.create_bets(session, data)
    return RedirectResponse(url="/", status_code=302)


@router.get("")
async def list_bets(
    session: AsyncSession = Depends(get_db),
    bet_type: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
):
    from datetime import date
    bets = await bet_service.list_resolved(
        session,
        bet_type,
        date.fromisoformat(date_from) if date_from else None,
        date.fromisoformat(date_to) if date_to else None,
        limit,
        offset,
    )
    return [
        {
            "id": str(b.id),
            "bet_date": b.bet_date.isoformat(),
            "game_name": b.game_name,
            "bet_type": b.bet_type.value,
            "stake": str(b.stake),
            "odd": str(b.odd),
            "result": b.result.value if b.result else None,
            "return_amount": str(b.return_amount) if b.return_amount is not None else None,
            "profit": str((b.return_amount or Decimal("0")) - b.stake),
            "group_id": str(b.group_id) if b.group_id else None,
            "notes": b.notes,
        }
        for b in bets
    ]


@router.patch("/{bet_id}/result")
async def update_result(
    bet_id: UUID,
    body: BetResultUpdate,
    session: AsyncSession = Depends(get_db),
):
    bet = await bet_service.resolve_bet(session, bet_id, body.result)
    return {
        "id": str(bet.id),
        "result": bet.result.value if bet.result else None,
        "return_amount": str(bet.return_amount) if bet.return_amount is not None else None,
    }


@router.put("/{bet_id}")
async def update_bet(
    bet_id: UUID,
    session: AsyncSession = Depends(get_db),
    game_name: str = Form(""),
    bet_date: str = Form(""),
    market: str = Form(""),
    stake: str = Form(""),
    odd: str = Form(""),
    result: str = Form(""),
):
    bet = await bet_service.update_bet(
        session,
        bet_id,
        bet_date=_parse_bet_datetime(bet_date),
        game_name=game_name if game_name else None,
        market=market if market else None,
        stake=Decimal(stake) if stake else None,
        odd=Decimal(odd) if odd else None,
        result=result,
    )
    return {
        "id": str(bet.id),
        "result": bet.result.value if bet.result else None,
        "return_amount": str(bet.return_amount) if bet.return_amount is not None else None,
    }


@router.delete("/{bet_id}")
async def delete_bet(bet_id: UUID, session: AsyncSession = Depends(get_db)):
    await bet_service.delete_bet(session, bet_id)
    return {"status": "deleted"}
