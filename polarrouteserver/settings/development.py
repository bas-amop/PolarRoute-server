import yaml
from pathlib import Path

from .base import *

with open(Path("config", "development.yaml"), "r") as f:
    config = yaml.load(f, Loader=yaml.Loader)

MESH_PATH = config.get("mesh_path")

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
