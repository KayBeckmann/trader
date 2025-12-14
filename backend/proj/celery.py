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
    # Fetch stock data every minute
    'fetch-stock-data-every-minute': {
        'task': 'proj.tasks.fetch_and_store_stock_data',
        'schedule': crontab(minute='*'),
    },
    # Open training trades (virtual positions) every 5 minutes
    'open-training-trades-every-5-minutes': {
        'task': 'proj.trading_tasks.open_trades',
        'schedule': crontab(minute='*/5'),
    },
    # Generate KNN predictions every minute
    'generate-knn-predictions-every-minute': {
        'task': 'proj.trading_tasks.generate_knn_predictions',
        'schedule': crontab(minute='*'),
    },
    # Create trades based on KNN predictions every minute
    'create-knn-trades-every-minute': {
        'task': 'proj.trading_tasks.create_knn_trades',
        'schedule': crontab(minute='*'),
    },
    # Evaluate trades every 30 seconds
    'evaluate-trades-every-30-seconds': {
        'task': 'proj.trading_tasks.evaluate_trades',
        'schedule': 30.0,
    },
    # Remove failed stocks daily at midnight
    'remove-failed-stocks-daily': {
        'task': 'proj.trading_tasks.remove_failed_stocks',
        'schedule': crontab(hour=0, minute=0),
    },
    # Fetch stock metadata hourly (name, ISIN, etc.)
    'fetch-stock-metadata-hourly': {
        'task': 'proj.tasks.fetch_stock_metadata',
        'schedule': crontab(minute=0),  # Every hour at minute 0
    },
}

if __name__ == '__main__':
    app.start()
