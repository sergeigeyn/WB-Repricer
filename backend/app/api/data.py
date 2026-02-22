"""Data collection endpoints."""

import logging

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/data", tags=["data"])
logger = logging.getLogger(__name__)


@router.post("/collect")
async def trigger_collection(
    _current_user: User = Depends(get_current_user),
):
    """Trigger full data collection via Celery (async, non-blocking)."""
    from app.tasks.celery_app import collect_all_data

    task = collect_all_data.delay()
    return {"task_id": task.id, "status": "started"}


@router.post("/collect-promotions")
async def trigger_promotions_collection(
    _current_user: User = Depends(get_current_user),
):
    """Trigger promotions sync via Celery."""
    from app.tasks.celery_app import collect_promotions

    task = collect_promotions.delay()
    return {"task_id": task.id, "status": "started"}


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    _current_user: User = Depends(get_current_user),
):
    """Check Celery task status."""
    from app.tasks.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": result.status,
        "result": None,
    }

    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["result"] = {"error": str(result.result)}

    return response
