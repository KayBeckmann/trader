from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.worker.tasks", "app.worker.trading_tasks"]
)

celery_app.conf.update(
    beat_schedule={
        'fetch-and-open-every-5-minutes': {
            'task': 'app.worker.tasks.fetch_and_store_stock_data',
            'schedule': 300.0,
            'options': {'link': 'app.worker.trading_tasks.open_trades'}
        },
        'evaluate-trades-every-5-minutes': {
            'task': 'app.worker.trading_tasks.evaluate_trades',
            'schedule': 300.0,
        },
    },
    timezone='UTC'
)
