"""Data collection endpoints."""

import logging

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.models.user import User
from app.services.data_collector import collect_all

router = APIRouter(prefix="/data", tags=["data"])
logger = logging.getLogger(__name__)


@router.post("/collect")
async def trigger_collection(
    _current_user: User = Depends(get_current_user),
):
    """Manually trigger data collection from WB API."""
    result = await collect_all()
    return result
