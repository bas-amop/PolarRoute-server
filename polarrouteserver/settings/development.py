import os

from .base import *

logger = logging.getLogger(__name__)

SECRET_KEY = "django-insecure-dutfial2$h()(2ivh5euo*t27*p3ukqso7f_-^&w831zq!oz-g"

DEBUG = True

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "assets/"),
]
