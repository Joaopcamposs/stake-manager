from datetime import date
from decimal import Decimal
from uuid import UUID

from models.bet import Bet, BetResult, BetType
from schemas.bet import BetCreate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid_extensions import uuid7


async def create_bets(session: AsyncSession, data: BetCreate) -> list[Bet]:
    bet_date = data.bet_date or date.today()
    bets: list[Bet] = []

    has_principal = data.principal_odd is not None and data.principal_odd > 0
    has_zoiao = data.zoiao_odd is not None and data.zoiao_odd > 0
    group_id = uuid7() if (has_principal and has_zoiao) else None

    def calc_return(stake: Decimal, odd: Decimal, res: BetResult | None) -> Decimal | None:
        if not res:
            return None
        match res:
            case BetResult.green:
                return stake * odd
            case BetResult.red:
                return Decimal("0")
            case BetResult.void:
                return stake

    if has_principal:
        stake = data.principal_stake or Decimal("100")
        p_result = BetResult(data.principal_result) if data.principal_result else None
        bet = Bet(
            bet_date=bet_date,
            game_name=data.game_name,
            bet_type=BetType.principal,
            market=data.principal_market,
            stake=stake,
            odd=data.principal_odd,
            result=p_result,
            return_amount=calc_return(stake, data.principal_odd, p_result),
            group_id=group_id,
            notes=data.notes,
        )
        session.add(bet)
        bets.append(bet)

    if has_zoiao:
        stake = data.zoiao_stake or Decimal("25")
        z_result = BetResult(data.zoiao_result) if data.zoiao_result else None
        bet = Bet(
            bet_date=bet_date,
            game_name=data.game_name,
            bet_type=BetType.zoiao,
            market=data.zoiao_market,
            stake=stake,
            odd=data.zoiao_odd,
            result=z_result,
            return_amount=calc_return(stake, data.zoiao_odd, z_result),
            group_id=group_id,
            notes=data.notes,
        )
        session.add(bet)
        bets.append(bet)

    await session.commit()
    return bets


async def resolve_bet(session: AsyncSession, bet_id: UUID, result: str) -> Bet:
    bet = await session.get(Bet, bet_id)
    if not bet:
        raise ValueError("Bet not found")

    bet.result = BetResult(result)

    match bet.result:
        case BetResult.green:
            bet.return_amount = bet.stake * bet.odd
        case BetResult.red:
            bet.return_amount = Decimal("0")
        case BetResult.void:
            bet.return_amount = bet.stake

    await session.commit()
    await session.refresh(bet)
    return bet


async def list_pending(session: AsyncSession) -> list[Bet]:
    stmt = select(Bet).where(Bet.result.is_(None)).order_by(Bet.id.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_resolved(
    session: AsyncSession,
    bet_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Bet]:
    stmt = select(Bet).where(Bet.result.is_not(None))

    if bet_type:
        stmt = stmt.where(Bet.bet_type == BetType(bet_type))
    if date_from:
        stmt = stmt.where(Bet.bet_date >= date_from)
    if date_to:
        stmt = stmt.where(Bet.bet_date <= date_to)

    stmt = stmt.order_by(Bet.id.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_bet(
    session: AsyncSession,
    bet_id: UUID,
    bet_date: date | None = None,
    game_name: str | None = None,
    market: str | None = None,
    stake: Decimal | None = None,
    odd: Decimal | None = None,
    result: str | None = None,
    notes: str | None = None,
) -> Bet:
    bet = await session.get(Bet, bet_id)
    if not bet:
        raise ValueError("Bet not found")

    if bet_date is not None:
        bet.bet_date = bet_date
    if game_name is not None:
        bet.game_name = game_name or None
    if market is not None:
        bet.market = market or None
    if stake is not None:
        bet.stake = stake
    if odd is not None:
        bet.odd = odd
    if notes is not None:
        bet.notes = notes or None

    if result is not None:
        if result == "":
            bet.result = None
            bet.return_amount = None
        else:
            bet.result = BetResult(result)
            match bet.result:
                case BetResult.green:
                    bet.return_amount = bet.stake * bet.odd
                case BetResult.red:
                    bet.return_amount = Decimal("0")
                case BetResult.void:
                    bet.return_amount = bet.stake

    await session.commit()
    await session.refresh(bet)
    return bet


async def delete_bet(session: AsyncSession, bet_id: UUID) -> None:
    bet = await session.get(Bet, bet_id)
    if not bet:
        raise ValueError("Bet not found")
    await session.delete(bet)
    await session.commit()
