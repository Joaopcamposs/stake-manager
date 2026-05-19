from datetime import date
from decimal import Decimal

import pytest
from models.bet import Bet, BetResult, BetType
from models.settings import AppSettings
from services import stats as stats_service
from sqlalchemy.ext.asyncio import AsyncSession


async def _seed_settings(session: AsyncSession):
    session.add(AppSettings(key="banca_inicial", value="1000"))
    await session.commit()


async def _create_bet(session: AsyncSession, **kwargs) -> Bet:
    defaults = {
        "bet_date": date(2025, 1, 15),
        "bet_type": BetType.principal,
        "stake": Decimal("100"),
        "odd": Decimal("1.80"),
        "result": BetResult.green,
        "return_amount": Decimal("180"),
    }
    defaults.update(kwargs)
    bet = Bet(**defaults)
    session.add(bet)
    await session.commit()
    return bet


@pytest.mark.asyncio
async def test_kpis_empty(session: AsyncSession):
    await _seed_settings(session)
    kpis = await stats_service.get_kpis(session)
    assert kpis.banca_atual == Decimal("1000.00")
    assert kpis.roi == Decimal("0.00")
    assert kpis.edge == Decimal("0.00")


@pytest.mark.asyncio
async def test_kpis_with_bets(session: AsyncSession):
    await _seed_settings(session)
    await _create_bet(
        session,
        result=BetResult.green,
        stake=Decimal("100"),
        odd=Decimal("2.00"),
        return_amount=Decimal("200"),
    )
    await _create_bet(
        session,
        result=BetResult.red,
        stake=Decimal("100"),
        odd=Decimal("1.80"),
        return_amount=Decimal("0"),
    )

    kpis = await stats_service.get_kpis(session)
    # green: +100, red: -100 = net 0
    assert kpis.banca_atual == Decimal("1000.00")
    assert kpis.lucro_liquido == Decimal("0.00")
    assert kpis.taxa_acerto == Decimal("50.00")
    assert kpis.streak_atual == 1
    assert kpis.streak_tipo == "red"


@pytest.mark.asyncio
async def test_timeseries(session: AsyncSession):
    await _seed_settings(session)
    await _create_bet(
        session,
        bet_date=date(2025, 1, 1),
        result=BetResult.green,
        stake=Decimal("100"),
        odd=Decimal("2.00"),
        return_amount=Decimal("200"),
    )

    points = await stats_service.get_timeseries(session)
    assert len(points) >= 1
    assert points[0].banca == Decimal("1100.00")
