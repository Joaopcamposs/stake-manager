from collections import defaultdict
from datetime import date
from decimal import Decimal

from models.bet import Bet, BetResult, BetType
from models.settings import AppSettings
from schemas.stats import (
    BetEvolutionPoint,
    HitRateByOdds,
    KPIResponse,
    MarketProfit,
    MarketResults,
    MonthlyResult,
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
    stmt = select(Bet).where(Bet.result.is_not(None)).where(Bet.result != BetResult.void)
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

    stake_medio = total_apostado / Decimal(total_resolved) if total_resolved else Decimal("0")

    return KPIResponse(
        banca_atual=banca_atual.quantize(Decimal("0.01")),
        banca_inicial=banca_inicial.quantize(Decimal("0.01")),
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
        total_apostas=total_resolved,
        stake_medio=stake_medio.quantize(Decimal("0.01")),
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
    for bet in bets:
        odd_str = str(bet.odd.normalize())
        bins[odd_str] += 1

    result: list[OddsDistributionBin] = []
    for key in sorted(bins.keys(), key=lambda x: Decimal(x)):
        val = Decimal(key)
        result.append(OddsDistributionBin(range_start=val, range_end=val, count=bins[key]))
    return result


async def get_hit_rate_by_odds(
    session: AsyncSession,
    bet_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[HitRateByOdds]:
    bets = await _resolved_bets(session, bet_type, date_from, date_to)

    brackets = [
        (Decimal("0"), Decimal("1.5"), "<1.5"),
        (Decimal("1.5"), Decimal("2.0"), "1.5-2.0"),
        (Decimal("2.0"), Decimal("2.5"), "2.0-2.5"),
        (Decimal("2.5"), Decimal("3.0"), "2.5-3.0"),
        (Decimal("3.0"), Decimal("4.0"), "3.0-4.0"),
        (Decimal("4.0"), Decimal("5.0"), "4.0-5.0"),
        (Decimal("5.0"), Decimal("999"), "5.0+"),
    ]

    data_map: dict[str, dict[str, int]] = {
        label: {"total": 0, "greens": 0} for _, _, label in brackets
    }

    for bet in bets:
        for start, end, label in brackets:
            if start <= bet.odd < end:
                data_map[label]["total"] += 1
                if bet.result == BetResult.green:
                    data_map[label]["greens"] += 1
                break

    result: list[HitRateByOdds] = []
    for _, _, label in brackets:
        data = data_map[label]
        if data["total"] == 0:
            continue
        rate = Decimal(data["greens"]) / Decimal(data["total"]) * 100
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


async def get_market_profit(
    session: AsyncSession,
    bet_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[MarketProfit]:
    bets = await _resolved_bets(session, bet_type, date_from, date_to)

    markets: dict[str, dict[str, Decimal | int]] = defaultdict(
        lambda: {"profit": Decimal("0"), "count": 0, "greens": 0}
    )
    for bet in bets:
        m = bet.market or "sem_mercado"
        profit = (bet.return_amount or Decimal("0")) - bet.stake
        markets[m]["profit"] += profit
        markets[m]["count"] += 1
        if bet.result == BetResult.green:
            markets[m]["greens"] += 1

    result: list[MarketProfit] = []
    for market, data in sorted(markets.items(), key=lambda x: x[1]["profit"], reverse=True):
        count = int(data["count"])
        greens = int(data["greens"])
        rate = Decimal(greens) / Decimal(count) * 100 if count else Decimal("0")
        result.append(
            MarketProfit(
                market=market,
                profit=Decimal(str(data["profit"])).quantize(Decimal("0.01")),
                count=count,
                rate=rate.quantize(Decimal("0.01")),
            )
        )
    return result


async def get_monthly_results(
    session: AsyncSession,
    bet_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[MonthlyResult]:
    bets = await _resolved_bets(session, bet_type, date_from, date_to)

    months: dict[str, dict[str, Decimal | int]] = defaultdict(
        lambda: {"profit": Decimal("0"), "count": 0}
    )
    for bet in bets:
        key = bet.bet_date.strftime("%Y-%m")
        profit = (bet.return_amount or Decimal("0")) - bet.stake
        months[key]["profit"] += profit
        months[key]["count"] += 1

    result: list[MonthlyResult] = []
    for month in sorted(months.keys()):
        data = months[month]
        result.append(
            MonthlyResult(
                month=month,
                profit=Decimal(str(data["profit"])).quantize(Decimal("0.01")),
                count=int(data["count"]),
            )
        )
    return result


async def get_market_results(
    session: AsyncSession,
    bet_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[MarketResults]:
    bets = await _resolved_bets(session, bet_type, date_from, date_to)

    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"greens": 0, "reds": 0})
    for bet in bets:
        m = bet.market or "sem_mercado"
        if bet.result == BetResult.green:
            counts[m]["greens"] += 1
        elif bet.result == BetResult.red:
            counts[m]["reds"] += 1

    result: list[MarketResults] = []
    for market, data in sorted(counts.items(), key=lambda x: x[1]["greens"] + x[1]["reds"], reverse=True):
        result.append(MarketResults(market=market, greens=data["greens"], reds=data["reds"]))
    return result


async def get_bet_evolution(
    session: AsyncSession,
    bet_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[BetEvolutionPoint]:
    banca_inicial = Decimal(await _get_setting(session, "banca_inicial", "1000"))
    bets = await _resolved_bets(session, bet_type, date_from, date_to)

    points: list[BetEvolutionPoint] = []
    running_banca = banca_inicial
    lucro_acumulado = Decimal("0")

    for i, bet in enumerate(bets):
        profit = (bet.return_amount or Decimal("0")) - bet.stake
        running_banca += profit
        lucro_acumulado += profit
        points.append(
            BetEvolutionPoint(
                index=i + 1,
                banca=running_banca.quantize(Decimal("0.01")),
                lucro_acumulado=lucro_acumulado.quantize(Decimal("0.01")),
                date=bet.bet_date,
                result=bet.result.value if bet.result else "void",
            )
        )

    return points
