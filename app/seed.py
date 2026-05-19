from db import async_session_factory
from models.settings import AppSettings

DEFAULTS = {
    "banca_inicial": "1000",
    "stake_principal_default": "100",
    "stake_zoiao_default": "25",
    "odd_minima": "1.5",
}


async def run_seed():
    async with async_session_factory() as session:
        for key, value in DEFAULTS.items():
            existing = await session.get(AppSettings, key)
            if not existing:
                session.add(AppSettings(key=key, value=value))
        await session.commit()
        print("Settings seeded.")
