from pathlib import Path

from celery.schedules import crontab

from .base import *

logger = logging.getLogger(__name__)

if MESH_DIR is None:
    pass
    # disabling these warnings in settings modules until we can resolve https://github.com/bas-amop/PolarRoute-server/issues/49
    # logger.warning(
    #     "POLARROUTE_MESH_DIR or POLARROUTE_MESH_METADATA_DIR not set, both are required to ingest new meshes into database.\n\
    #                No new meshes will be automatically ingested."
    # )
else:
    if MESH_METADATA_DIR is None:
        MESH_METADATA_DIR = MESH_DIR
        # logger.warning(
        #     f"POLARROUTE_MESH_METADATA_DIR not set. Using POLARROUTE_MESH_DIR as POLARROUTE_MESH_METADATA_DIR: {MESH_DIR}"
        # )

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
            "level": os.getenv("POLARROUTE_LOG_LEVEL", "INFO"),
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
