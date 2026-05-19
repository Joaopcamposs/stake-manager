from fastapi import APIRouter
from routes.bets import router as bets_router
from routes.stats import router as stats_router
from routes.views import router as views_router

router = APIRouter()
router.include_router(views_router)
router.include_router(bets_router)
router.include_router(stats_router)
