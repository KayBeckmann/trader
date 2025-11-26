from celery import Celery
from celery.schedules import crontab

app = Celery('proj',
             broker='redis://redis:6379/0',
             backend='redis://redis:6379/0',
             include=['proj.tasks', 'proj.trading_tasks'])

app.conf.update(
    result_expires=3600,
)

app.conf.beat_schedule = {
    'fetch-stock-data-every-minute': {
        'task': 'proj.tasks.fetch_and_store_stock_data',
        'schedule': crontab(minute='*'),
    },
    'generate-dummy-knn-results-every-minute': {
        'task': 'proj.trading_tasks.generate_dummy_knn_results',
        'schedule': crontab(minute='*'),
    },
    'create-knn-trades-every-minute': {
        'task': 'proj.trading_tasks.create_knn_trades',
        'schedule': crontab(minute='*'),
    },
    'evaluate-trades-every-30-seconds': {
        'task': 'proj.trading_tasks.evaluate_trades',
        'schedule': 30.0,
    },
}

if __name__ == '__main__':
    app.start()
