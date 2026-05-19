from collections import defaultdict
from datetime import date
from decimal import Decimal

from models.bet import Bet, BetResult, BetType
from models.settings import AppSettings
from schemas.stats import (
    HitRateByOdds,
    KPIResponse,
    OddsDistributionBin,
    ProfitByTypePoint,
    TimeseriesPoint,
    WeekdayResult,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _get_setting(session: AsyncSession, key: str, default: str = "0") -> str:
    stmt = select(AppSettings).where(AppSettings.key == key)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row.value if row else default


async def _resolved_bets(
    session: AsyncSession,
    bet_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[Bet]:
    stmt = select(Bet).where(Bet.result.is_not(None))
    if bet_type:
        stmt = stmt.where(Bet.bet_type == BetType(bet_type))
    if date_from:
        stmt = stmt.where(Bet.bet_date >= date_from)
    if date_to:
        stmt = stmt.where(Bet.bet_date <= date_to)
    stmt = stmt.order_by(Bet.bet_date, Bet.created_at)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_kpis(
    session: AsyncSession,
    bet_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> KPIResponse:
    banca_inicial = Decimal(await _get_setting(session, "banca_inicial", "1000"))
    bets = await _resolved_bets(session, bet_type, date_from, date_to)

    total_apostado = Decimal("0")
    lucro_liquido = Decimal("0")
    greens = 0
    reds = 0
    weighted_odds_sum = Decimal("0")
    weighted_stake_sum = Decimal("0")

    # For streak
    results_ordered: list[str] = []
    # For drawdown
    running_banca = banca_inicial
    peak = banca_inicial
    max_drawdown = Decimal("0")

    for bet in bets:
        if bet.result == BetResult.void:
            continue

        total_apostado += bet.stake
        profit = (bet.return_amount or Decimal("0")) - bet.stake
        lucro_liquido += profit
        weighted_odds_sum += bet.odd * bet.stake
        weighted_stake_sum += bet.stake

        if bet.result == BetResult.green:
            greens += 1
            results_ordered.append("green")
        elif bet.result == BetResult.red:
            reds += 1
            results_ordered.append("red")

        running_banca += profit
        if running_banca > peak:
            peak = running_banca
        dd = peak - running_banca
        if dd > max_drawdown:
            max_drawdown = dd

    banca_atual = banca_inicial + lucro_liquido
    variacao_pct = (lucro_liquido / banca_inicial * 100) if banca_inicial else Decimal("0")
    total_resolved = greens + reds
    roi = (lucro_liquido / total_apostado * 100) if total_apostado else Decimal("0")
    taxa_acerto = (
        Decimal(greens) / Decimal(total_resolved) * 100 if total_resolved else Decimal("0")
    )
    odd_media = weighted_odds_sum / weighted_stake_sum if weighted_stake_sum else Decimal("0")
    breakeven = (Decimal("1") / odd_media * 100) if odd_media else Decimal("0")
    edge = taxa_acerto - breakeven

    # Streak
    streak_atual = 0
    streak_tipo = "none"
    if results_ordered:
        last = results_ordered[-1]
        streak_tipo = last
        for r in reversed(results_ordered):
            if r == last:
                streak_atual += 1
            else:
                break

    return KPIResponse(
        banca_atual=banca_atual.quantize(Decimal("0.01")),
        variacao_pct=variacao_pct.quantize(Decimal("0.01")),
        total_apostado=total_apostado.quantize(Decimal("0.01")),
        lucro_liquido=lucro_liquido.quantize(Decimal("0.01")),
        roi=roi.quantize(Decimal("0.01")),
        taxa_acerto=taxa_acerto.quantize(Decimal("0.01")),
        odd_media_ponderada=odd_media.quantize(Decimal("0.001")),
        breakeven=breakeven.quantize(Decimal("0.01")),
        edge=edge.quantize(Decimal("0.01")),
        streak_atual=streak_atual,
        streak_tipo=streak_tipo,
        drawdown_maximo=max_drawdown.quantize(Decimal("0.01")),
    )


async def get_timeseries(
    session: AsyncSession,
    bet_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[TimeseriesPoint]:
    banca_inicial = Decimal(await _get_setting(session, "banca_inicial", "1000"))
    bets = await _resolved_bets(session, bet_type, date_from, date_to)

    daily_profit: dict[date, Decimal] = defaultdict(Decimal)
    for bet in bets:
        profit = (bet.return_amount or Decimal("0")) - bet.stake
        daily_profit[bet.bet_date] += profit

    points: list[TimeseriesPoint] = []
    running = banca_inicial
    for d in sorted(daily_profit.keys()):
        running += daily_profit[d]
        points.append(TimeseriesPoint(date=d, banca=running.quantize(Decimal("0.01"))))

    return points


async def get_profit_by_type(
    session: AsyncSession,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[ProfitByTypePoint]:
    bets = await _resolved_bets(session, None, date_from, date_to)

    def _empty_type_dict():
        return {"principal": Decimal("0"), "zoiao": Decimal("0")}

    daily: dict[date, dict[str, Decimal]] = defaultdict(_empty_type_dict)
    for bet in bets:
        profit = (bet.return_amount or Decimal("0")) - bet.stake
        daily[bet.bet_date][bet.bet_type.value] += profit

    points: list[ProfitByTypePoint] = []
    acc_principal = Decimal("0")
    acc_zoiao = Decimal("0")
    for d in sorted(daily.keys()):
        acc_principal += daily[d]["principal"]
        acc_zoiao += daily[d]["zoiao"]
        points.append(
            ProfitByTypePoint(
                date=d,
                principal=acc_principal.quantize(Decimal("0.01")),
                zoiao=acc_zoiao.quantize(Decimal("0.01")),
            )
        )

    return points


async def get_odds_distribution(
    session: AsyncSession,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[OddsDistributionBin]:
    bets = await _resolved_bets(session, None, date_from, date_to)

    bins: dict[str, int] = defaultdict(int)
    step = Decimal("0.1")
    for bet in bets:
        bucket = (bet.odd / step).to_integral_value() * step
        key = str(bucket)
        bins[key] += 1

    result: list[OddsDistributionBin] = []
    for key in sorted(bins.keys(), key=lambda x: Decimal(x)):
        start = Decimal(key)
        result.append(
            OddsDistributionBin(
                range_start=start,
                range_end=start + step,
                count=bins[key],
            )
        )
    return result


async def get_hit_rate_by_odds(
    session: AsyncSession,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[HitRateByOdds]:
    bets = await _resolved_bets(session, None, date_from, date_to)

    brackets: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "greens": 0})
    step = Decimal("0.1")
    for bet in bets:
        if bet.result == BetResult.void:
            continue
        bucket = (bet.odd / step).to_integral_value() * step
        label = f"{bucket}-{bucket + step}"
        brackets[label]["total"] += 1
        if bet.result == BetResult.green:
            brackets[label]["greens"] += 1

    result: list[HitRateByOdds] = []
    for label in sorted(brackets.keys(), key=lambda x: Decimal(x.split("-")[0])):
        data = brackets[label]
        rate = (
            Decimal(data["greens"]) / Decimal(data["total"]) * 100
            if data["total"]
            else Decimal("0")
        )
        result.append(
            HitRateByOdds(
                range_label=label,
                total=data["total"],
                greens=data["greens"],
                rate=rate.quantize(Decimal("0.01")),
            )
        )
    return result


async def get_weekday_results(
    session: AsyncSession,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[WeekdayResult]:
    bets = await _resolved_bets(session, None, date_from, date_to)

    weekdays: dict[int, dict[str, Decimal | int]] = defaultdict(
        lambda: {"profit": Decimal("0"), "count": 0}
    )
    for bet in bets:
        wd = bet.bet_date.weekday()
        profit = (bet.return_amount or Decimal("0")) - bet.stake
        weekdays[wd]["profit"] += profit
        weekdays[wd]["count"] += 1

    names = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    result: list[WeekdayResult] = []
    for wd in range(7):
        data = weekdays[wd]
        result.append(
            WeekdayResult(
                weekday=wd,
                weekday_name=names[wd],
                profit=Decimal(str(data["profit"])).quantize(Decimal("0.01")),
                count=int(data["count"]),
            )
        )
    return result
