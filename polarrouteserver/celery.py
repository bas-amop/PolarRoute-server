import os
import logging
from pathlib import Path

from celery import Celery, signals
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "polarrouteserver.settings.development")

app = Celery("polarrouteserver")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


@signals.setup_logging.connect
def on_celery_setup_logging(**kwargs):
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s%(process)d/%(thread)d%(name)s%(funcName)s %(lineno)s%(levelname)s%(message)s",
                "datefmt": "%Y/%m/%d %H:%M:%S",
            }
        },
        "handlers": {
            "celery": {
                "level": "INFO",
                "class": "logging.FileHandler",
                "filename": Path(settings.BASE_DIR, "logs", "celery.log"),
                "formatter": "default",
            },
            "default": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
        },
        "loggers": {
            "celery": {"handlers": ["celery"], "level": "INFO", "propagate": False},
        },
        "root": {"handlers": ["default"], "level": "DEBUG"},
    }

    logging.config.dictConfig(config)
