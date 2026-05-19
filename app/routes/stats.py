from datetime import date, timedelta

from db import get_db
from fastapi import APIRouter, Depends, Query
from services import stats as stats_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _parse_period(period: str | None) -> tuple[date | None, date | None]:
    if not period or period == "all":
        return None, None
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(period)
    if days:
        return date.today() - timedelta(days=days), date.today()
    return None, None


@router.get("")
async def kpis(
    session: AsyncSession = Depends(get_db),
    period: str | None = Query(None),
    bet_type: str | None = Query(None),
):
    date_from, date_to = _parse_period(period)
    result = await stats_service.get_kpis(session, bet_type, date_from, date_to)
    return result.model_dump()


@router.get("/timeseries")
async def timeseries(
    session: AsyncSession = Depends(get_db),
    period: str | None = Query(None),
    bet_type: str | None = Query(None),
):
    date_from, date_to = _parse_period(period)
    points = await stats_service.get_timeseries(session, bet_type, date_from, date_to)
    return [p.model_dump() for p in points]


@router.get("/profit-by-type")
async def profit_by_type(
    session: AsyncSession = Depends(get_db),
    period: str | None = Query(None),
):
    date_from, date_to = _parse_period(period)
    points = await stats_service.get_profit_by_type(session, date_from, date_to)
    return [p.model_dump() for p in points]


@router.get("/odds-distribution")
async def odds_distribution(
    session: AsyncSession = Depends(get_db),
    period: str | None = Query(None),
):
    date_from, date_to = _parse_period(period)
    bins = await stats_service.get_odds_distribution(session, date_from, date_to)
    return [b.model_dump() for b in bins]


@router.get("/hit-rate-by-odds")
async def hit_rate_by_odds(
    session: AsyncSession = Depends(get_db),
    period: str | None = Query(None),
    bet_type: str | None = Query(None),
):
    date_from, date_to = _parse_period(period)
    data = await stats_service.get_hit_rate_by_odds(session, bet_type, date_from, date_to)
    return [d.model_dump() for d in data]


@router.get("/weekday")
async def weekday_results(
    session: AsyncSession = Depends(get_db),
    period: str | None = Query(None),
):
    date_from, date_to = _parse_period(period)
    data = await stats_service.get_weekday_results(session, date_from, date_to)
    return [d.model_dump() for d in data]


@router.get("/market-profit")
async def market_profit(
    session: AsyncSession = Depends(get_db),
    period: str | None = Query(None),
    bet_type: str | None = Query(None),
):
    date_from, date_to = _parse_period(period)
    data = await stats_service.get_market_profit(session, bet_type, date_from, date_to)
    return [d.model_dump() for d in data]


@router.get("/monthly")
async def monthly_results(
    session: AsyncSession = Depends(get_db),
    period: str | None = Query(None),
    bet_type: str | None = Query(None),
):
    date_from, date_to = _parse_period(period)
    data = await stats_service.get_monthly_results(session, bet_type, date_from, date_to)
    return [d.model_dump() for d in data]


@router.get("/evolution")
async def bet_evolution(
    session: AsyncSession = Depends(get_db),
    period: str | None = Query(None),
    bet_type: str | None = Query(None),
):
    date_from, date_to = _parse_period(period)
    data = await stats_service.get_bet_evolution(session, bet_type, date_from, date_to)
    return [d.model_dump() for d in data]
