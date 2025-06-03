"""
WSGI config for polarrouteserver project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "polarrouteserver.settings.production")


def application(environ, start_response):
    # pass the WSGI environment variables on through to os.environ
    for key in environ:
        if key.startswith(("POLARROUTE_", "DJANGO_", "CELERY_")):
            os.environ[key] = environ[key]
    return get_wsgi_application()(environ, start_response)
