from .base import *

logger = logging.getLogger(__name__)

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
