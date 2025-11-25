from celery import Celery

app = Celery('proj',
             broker='redis://redis:6379/0',
             backend='redis://redis:6379/0',
             include=['proj.tasks', 'proj.trading_tasks'])

app.conf.update(
    result_expires=3600,
)

if __name__ == '__main__':
    app.start()
