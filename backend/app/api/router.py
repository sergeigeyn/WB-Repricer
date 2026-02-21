"""Main API router combining all sub-routers."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.data import router as data_router
from app.api.health import router as health_router
from app.api.products import router as products_router
from app.api.promotions import router as promotions_router
from app.api.settings import router as settings_router
from app.api.strategies import router as strategies_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(products_router)
api_router.include_router(promotions_router)
api_router.include_router(strategies_router)
api_router.include_router(settings_router)
api_router.include_router(data_router)
