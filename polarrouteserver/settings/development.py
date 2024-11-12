import logging
import os
from pathlib import Path
import yaml

from .base import *

logger = logging.getLogger(__name__)

try:
    with open(Path("config", "development.yaml"), "r") as f:
        config = yaml.load(f, Loader=yaml.Loader)

    MESH_PATH = config.get("mesh_path", None)
    MESH_DIR = config.get("mesh_dir", None)
except FileNotFoundError:
    logger.info(
        "No config file found. Falling back on defaults or environment variables."
    )
    MESH_PATH = os.getenv("POLARROUTE_MESH_PATH")
    MESH_DIR = os.getenv("POLARROUTE_MESH_DIR")

if MESH_DIR is None:
    logger.warning(
        "MESH_DIR not set, this is required to ingest new meshes into database.\n\
                   No new meshes will be automatically ingested."
    )

# Use django-cors-headers package in development
INSTALLED_APPS.append("corsheaders")
MIDDLEWARE += [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:9000",
]
CORS_ALLOW_METHODS = ("DELETE", "GET", "POST", "OPTIONS")
