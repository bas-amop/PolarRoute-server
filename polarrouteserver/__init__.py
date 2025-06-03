# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app
from . import route_api  # noqa

__all__ = ("celery_app",)
