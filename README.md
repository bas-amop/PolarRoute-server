# PolarRoute Server

**Note**: This is a work in progress and may change significantly.

A web server to manage requests for meshes and routes generated using the PolarRoute and MeshiPhi libraries,
implemented using Django, Celery and Django REST framework.

## Setup/installation for development

Depends on: python v3.11, docker for running rabbitmq (at present)

1. Clone this repository.
1. Inside a virtual environment or machine: `pip install -r requirements.txt`
1. Before first use, create the database by running `python manage.py migrate`
1. Use docker to start the rabbitmq server: `docker run -d -p 5672:5672 rabbitmq`
1. In one process or shell, start the celery server: `celery -A polarrouteserver worker -l INFO`
1. Set the environment variable defining which settings to use: `export DJANGO_SETTINGS_MODULE=polarrouteserver.settings.development`
1. In another process or shell, start the Django development server `python manage.py runserver`

For development, also install and use the development tools:
1. `pip install -r requirements.dev.txt`
1. `pre-commit install`
