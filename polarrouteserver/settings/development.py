import os

from .base import *

logger = logging.getLogger(__name__)

SECRET_KEY = "django-insecure-dutfial2$h()(2ivh5euo*t27*p3ukqso7f_-^&w831zq!oz-g"

DEBUG = True


STATIC_URL = "/static/"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "assets/"),
]

INTERNAL_IPS = [
    "localhost",
    "0.0.0.0",
    "127.0.0.1",
]

# required for correct INTERNAL_IPS setting in docker container
import socket #noqa

hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]

MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

INSTALLED_APPS.append("debug_toolbar")
