from datetime import date, datetime
from zoneinfo import ZoneInfo

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")


def today_sp() -> date:
    """Return the current date in São Paulo timezone."""
    return datetime.now(SAO_PAULO_TZ).date()


def now_sp() -> datetime:
    """Return the current datetime in São Paulo timezone."""
    return datetime.now(SAO_PAULO_TZ)
