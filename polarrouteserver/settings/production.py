from pathlib import Path

from celery.schedules import crontab

from .base import *

logger = logging.getLogger(__name__)

if not MESH_DIR:
    raise UserWarning(
        "POLARROUTE_MESH_DIR not set, this is required to ingest new meshes into database.\n\
                   No new meshes will be automatically ingested."
    )
else:
    CELERY_BEAT_SCHEDULE = {
        "import_meshes": {
            "task": "polarrouteserver.route_api.tasks.import_new_meshes",
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
            "filename": os.path.join(
                os.getenv("POLARROUTE_LOG_DIR", Path(BASE_DIR, "logs")),
                "polarrouteserver.log",
            ),
            "formatter": "verbose",
        },
    },
    "loggers": {
        "root": {
            "handlers": ["console", "file"],
            "level": os.getenv("POLARROUTE_LOG_LEVEL", "INFO"),
            "propagate": True,
        },
    },
}


CELERY_LOGGING = {
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
            "filename": os.path.join(
                os.getenv("POLARROUTE_LOG_DIR", Path(BASE_DIR, "logs")),
                "celery.log",
            ),
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

STATIC_ROOT = os.getenv("POLARROUTE_STATIC_ROOT", None)