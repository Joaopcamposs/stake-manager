from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class KPIResponse(BaseModel):
    banca_atual: Decimal
    variacao_pct: Decimal
    total_apostado: Decimal
    lucro_liquido: Decimal
    roi: Decimal
    taxa_acerto: Decimal
    odd_media_ponderada: Decimal
    breakeven: Decimal
    edge: Decimal
    streak_atual: int
    streak_tipo: str
    drawdown_maximo: Decimal


class TimeseriesPoint(BaseModel):
    date: date
    banca: Decimal


class ProfitByTypePoint(BaseModel):
    date: date
    principal: Decimal
    zoiao: Decimal


class OddsDistributionBin(BaseModel):
    range_start: Decimal
    range_end: Decimal
    count: int


class HitRateByOdds(BaseModel):
    range_label: str
    total: int
    greens: int
    rate: Decimal


class WeekdayResult(BaseModel):
    weekday: int
    weekday_name: str
    profit: Decimal
    count: int
