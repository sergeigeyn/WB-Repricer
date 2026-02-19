"""Celery application configuration."""

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
    # Collect orders every 4 hours
    "collect-orders": {
        "task": "app.tasks.data_collector.collect_orders",
        "schedule": crontab(hour="*/4", minute=15),
    },
    # Collect promotions once a day
    "collect-promotions": {
        "task": "app.tasks.data_collector.collect_promotions",
        "schedule": crontab(hour=5, minute=0),
    },
}


@celery_app.task(name="app.tasks.data_collector.collect_all_data")
def collect_all_data():
    """Placeholder: collect prices, stocks, sales from WB API."""
    return {"status": "ok", "task": "collect_all_data"}


@celery_app.task(name="app.tasks.data_collector.collect_orders")
def collect_orders():
    """Placeholder: collect orders from WB API."""
    return {"status": "ok", "task": "collect_orders"}


@celery_app.task(name="app.tasks.data_collector.collect_promotions")
def collect_promotions():
    """Placeholder: collect promotions from WB API."""
    return {"status": "ok", "task": "collect_promotions"}


@celery_app.task(name="app.tasks.price_updater.run_all_strategies")
def run_all_strategies():
    """Placeholder: execute all active pricing strategies."""
    return {"status": "ok", "task": "run_all_strategies"}
