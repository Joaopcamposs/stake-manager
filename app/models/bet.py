import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from db import Base
from sqlalchemy import Date, DateTime, Enum, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid_extensions import uuid7


class BetType(enum.StrEnum):
    principal = "principal"
    zoiao = "zoiao"


class BetResult(enum.StrEnum):
    green = "green"
    red = "red"
    void = "void"


class BetMarket(enum.StrEnum):
    over_0_5 = "over_0_5"
    over_1_5 = "over_1_5"
    over_2_5 = "over_2_5"
    over_3_5 = "over_3_5"
    over_4_5 = "over_4_5"
    over_5_5 = "over_5_5"
    over_6_5 = "over_6_5"
    over_7_5 = "over_7_5"
    over_8_5 = "over_8_5"
    asiatico_1 = "asiatico_1"
    asiatico_2 = "asiatico_2"
    asiatico_3 = "asiatico_3"
    asiatico_4 = "asiatico_4"
    asiatico_5 = "asiatico_5"
    asiatico_6 = "asiatico_6"
    asiatico_7 = "asiatico_7"
    asiatico_8 = "asiatico_8"


class Bet(Base):
    __tablename__ = "bets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    bet_date: Mapped[date] = mapped_column(Date)
    game_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    bet_type: Mapped[BetType] = mapped_column(Enum(BetType, native_enum=False))
    market: Mapped[str | None] = mapped_column(Text, nullable=True)
    stake: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    odd: Mapped[Decimal] = mapped_column(Numeric(6, 3))
    result: Mapped[BetResult | None] = mapped_column(
        Enum(BetResult, native_enum=False), nullable=True
    )
    return_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    group_id: Mapped[UUID | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
