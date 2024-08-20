from .base import *

CELERY_RESULT_BACKEND = (
    "db+postgresql+psycopg://postgres:polarroute@localhost:5432/test_polarrouteserver"
)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_STORE_EAGER_RESULT = True
