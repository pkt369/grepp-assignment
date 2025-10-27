"""
Celery configuration for the project.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure broker and result backend
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_DB_CELERY = 2  # Use separate DB for Celery

app.conf.broker_url = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_CELERY}'
app.conf.result_backend = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_CELERY}'

# Configure timezone
app.conf.timezone = 'Asia/Seoul'

# Configure beat schedule
app.conf.beat_schedule = {
    'sync-registration-counts': {
        'task': 'common.tasks.sync_registration_counts',
        'schedule': crontab(minute='*'),  # Run every minute
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
