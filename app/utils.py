from datetime import date, datetime
from zoneinfo import ZoneInfo

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")


def today_sp() -> date:
    """Return the current date in São Paulo timezone (America/Sao_Paulo, UTC-3)."""
    return datetime.now(SAO_PAULO_TZ).date()
