from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, model_validator


class BetCreate(BaseModel):
    game_name: str | None = None
    bet_date: datetime | None = None  # full datetime with time; defaults to now in SP tz
    principal_stake: Decimal | None = None
    principal_odd: Decimal | None = None
    principal_market: str | None = None
    principal_result: str | None = None
    zoiao_stake: Decimal | None = None
    zoiao_odd: Decimal | None = None
    zoiao_market: str | None = None
    zoiao_result: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def at_least_one_bet(self):
        has_principal = self.principal_odd is not None and self.principal_odd > 0
        has_zoiao = self.zoiao_odd is not None and self.zoiao_odd > 0
        if not has_principal and not has_zoiao:
            raise ValueError("Pelo menos uma aposta (principal ou zoião) deve ter odd preenchida")
        return self


class BetResponse(BaseModel):
    id: UUID
    created_at: str
    bet_date: datetime
    game_name: str | None
    bet_type: str
    stake: Decimal
    odd: Decimal
    result: str | None
    return_amount: Decimal | None
    group_id: UUID | None
    notes: str | None
    profit: Decimal | None = None

    model_config = {"from_attributes": True}


class BetResultUpdate(BaseModel):
    result: str
