from __future__ import absolute_import, unicode_literals

import datetime
import os
from datetime import timedelta

from celery.schedules import crontab
from celery.task import task
from celery import Celery

from entrebiz import settings


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'entrebiz.settings')

app = Celery('entrebiz')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
# app.autodiscover_tasks()
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
app.conf.beat_schedule = {
    'task_currency_conversion': {
        'task': 'currency_conversion',
        "schedule": crontab(hour='10, 17',
                            minute=0,
                            )
    },
    'task_check_transaction_status': {
        'task': 'check_transaction_status',
        'schedule': crontab(hour=11, minute=00),
    },
    'task_check_wallet_transaction_status': {
        'task': 'check_wallet_transaction_status',
        'schedule': crontab(hour=10, minute=00),
    },

}


@task(name="currency_conversion")
def task_currency_conversion():
    from entrebiz.celery_tasks import currency_conversion
    currency_conversion()


@task(name="check_transaction_status")
def task_check_transaction_status():
    from entrebiz.celery_tasks import check_transaction_status
    check_transaction_status()

@task(name="check_wallet_transaction_status")
def task_check_wallet_transaction_status():
    from entrebiz.celery_tasks import check_wallet_transaction_status
    check_wallet_transaction_status()