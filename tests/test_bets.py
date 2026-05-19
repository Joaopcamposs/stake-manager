from decimal import Decimal

import pytest
from models.bet import BetResult, BetType
from schemas.bet import BetCreate
from services import bets as bet_service
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_single_bet(session: AsyncSession):
    data = BetCreate(principal_odd=Decimal("1.85"), principal_stake=Decimal("100"))
    bets = await bet_service.create_bets(session, data)
    assert len(bets) == 1
    assert bets[0].bet_type == BetType.principal
    assert bets[0].stake == Decimal("100")
    assert bets[0].group_id is None


@pytest.mark.asyncio
async def test_create_double_bet(session: AsyncSession):
    data = BetCreate(
        game_name="Flamengo x Palmeiras",
        principal_odd=Decimal("1.85"),
        principal_stake=Decimal("100"),
        zoiao_odd=Decimal("3.50"),
        zoiao_stake=Decimal("25"),
    )
    bets = await bet_service.create_bets(session, data)
    assert len(bets) == 2
    assert bets[0].group_id is not None
    assert bets[0].group_id == bets[1].group_id
    assert bets[0].bet_type == BetType.principal
    assert bets[1].bet_type == BetType.zoiao


@pytest.mark.asyncio
async def test_resolve_green(session: AsyncSession):
    data = BetCreate(principal_odd=Decimal("2.00"), principal_stake=Decimal("50"))
    bets = await bet_service.create_bets(session, data)
    bet = await bet_service.resolve_bet(session, bets[0].id, "green")
    assert bet.result == BetResult.green
    assert bet.return_amount == Decimal("100.00")


@pytest.mark.asyncio
async def test_resolve_red(session: AsyncSession):
    data = BetCreate(principal_odd=Decimal("1.80"), principal_stake=Decimal("100"))
    bets = await bet_service.create_bets(session, data)
    bet = await bet_service.resolve_bet(session, bets[0].id, "red")
    assert bet.result == BetResult.red
    assert bet.return_amount == Decimal("0")


@pytest.mark.asyncio
async def test_resolve_void(session: AsyncSession):
    data = BetCreate(principal_odd=Decimal("1.80"), principal_stake=Decimal("100"))
    bets = await bet_service.create_bets(session, data)
    bet = await bet_service.resolve_bet(session, bets[0].id, "void")
    assert bet.result == BetResult.void
    assert bet.return_amount == Decimal("100")


@pytest.mark.asyncio
async def test_list_pending(session: AsyncSession):
    data = BetCreate(principal_odd=Decimal("1.80"))
    await bet_service.create_bets(session, data)
    pending = await bet_service.list_pending(session)
    assert len(pending) >= 1
    assert all(b.result is None for b in pending)


@pytest.mark.asyncio
async def test_delete_bet(session: AsyncSession):
    data = BetCreate(principal_odd=Decimal("1.80"))
    bets = await bet_service.create_bets(session, data)
    await bet_service.delete_bet(session, bets[0].id)
    remaining = await bet_service.list_pending(session)
    assert bets[0].id not in [b.id for b in remaining]
