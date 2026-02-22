"""Celery application configuration."""

import asyncio

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "priceforge",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Scheduled tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Collect prices and stocks twice a day (9:00 and 18:00 Moscow time = 6:00 and 15:00 UTC)
    "collect-data-morning": {
        "task": "app.tasks.data_collector.collect_all_data",
        "schedule": crontab(hour=6, minute=0),
    },
    "collect-data-evening": {
        "task": "app.tasks.data_collector.collect_all_data",
        "schedule": crontab(hour=15, minute=0),
    },
    # Run pricing strategies after data collection
    "run-strategies-morning": {
        "task": "app.tasks.price_updater.run_all_strategies",
        "schedule": crontab(hour=6, minute=30),
    },
    "run-strategies-evening": {
        "task": "app.tasks.price_updater.run_all_strategies",
        "schedule": crontab(hour=15, minute=30),
    },
    # Collect orders every 15 minutes (keep today's data fresh)
    "collect-orders": {
        "task": "app.tasks.data_collector.collect_orders",
        "schedule": crontab(minute="*/15"),
    },
    # Collect promotions once a day
    "collect-promotions": {
        "task": "app.tasks.data_collector.collect_promotions",
        "schedule": crontab(hour=5, minute=0),
    },
}


def _run_async(coro_func, *args, **kwargs):
    """Run async function in a fresh event loop with clean DB connection pool.

    Each Celery task gets a new event loop, but SQLAlchemy's async engine
    pools connections bound to a specific loop. Disposing the pool before
    each task ensures fresh connections on the new loop.
    """
    async def _wrapper():
        from app.core.database import engine

        await engine.dispose()
        return await coro_func(*args, **kwargs)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_wrapper())
    finally:
        loop.close()


@celery_app.task(
    name="app.tasks.data_collector.collect_all_data",
    soft_time_limit=600,
    time_limit=660,
)
def collect_all_data():
    """Collect products, prices, stocks, orders, commissions, storage, promotions from WB API."""
    from app.services.data_collector import collect_all

    return _run_async(collect_all)


@celery_app.task(name="app.tasks.data_collector.collect_orders")
def collect_orders():
    """Sync orders from WB Statistics API (lightweight, runs every 15 min)."""
    from app.services.data_collector import collect_orders_only

    return _run_async(collect_orders_only)


@celery_app.task(name="app.tasks.data_collector.collect_promotions")
def collect_promotions():
    """Sync promotions and promotion products from WB Calendar API."""
    from app.services.data_collector import collect_promotions_only

    return _run_async(collect_promotions_only)


@celery_app.task(name="app.tasks.price_updater.run_all_strategies")
def run_all_strategies():
    """Execute all active pricing strategies."""
    from app.services.strategies.runner import run_all_active_strategies

    return _run_async(run_all_active_strategies, triggered_by="schedule")
