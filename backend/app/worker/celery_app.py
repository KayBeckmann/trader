from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.worker.tasks"]
)

celery_app.conf.beat_schedule = {
    'fetch-stock-data-every-5-minutes': {
        'task': 'app.worker.tasks.fetch_and_store_stock_data',
        'schedule': 300.0,  # 5 minutes in seconds
    },
}
celery_app.conf.timezone = 'UTC'
