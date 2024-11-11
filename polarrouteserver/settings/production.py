import logging
import os
from pathlib import Path
import yaml

from celery.schedules import crontab

from .base import *

logger = logging.getLogger(__name__)

DEBUG = False

try:
    with open(Path("config", "production.yaml"), "r") as f:
        config = yaml.load(f, Loader=yaml.Loader)

    MESH_PATH = config.get("mesh_path")
    MESH_DIR = config.get("mesh_dir")

    ALLOWED_HOSTS.extend(config.get("allowed_hosts"))
except FileNotFoundError:
    logger.info(
        "No config file found. Falling back on defaults or environment variables."
    )

MESH_PATH = os.getenv("POLARROUTE_MESH_PATH")
MESH_DIR = os.getenv("POLARROUTE_MESH_DIR")
ALLOWED_HOSTS.extend(os.getenv("POLARROUTE_ALLOWED_HOSTS"))

CELERY_BROKER_URL = config.get("celery_broker_url")

CELERY_BEAT_SCHEDULE = {
    "sample_task": {
        "task": "route_api.tasks.import_new_meshes",
        "schedule": crontab(minute="*/10"),
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {process:d} {module} {levelname} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(BASE_DIR, "logs", "django.log"),
            "formatter": "verbose",
        },
    },
    "loggers": {
        "root": {
            "handlers": ["console", "file"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": True,
        },
    },
}
