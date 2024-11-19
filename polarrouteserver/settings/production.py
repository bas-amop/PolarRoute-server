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
