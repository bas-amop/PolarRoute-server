# PolarRoute Server

**Note**: This is a work in progress and may change significantly.

A web server to manage requests for meshes and routes generated using the PolarRoute and MeshiPhi libraries,
implemented using Django, Celery and Django REST framework.

## Setup/installation for development

Depends on: python v3.11, [docker](https://docs.docker.com/get-docker/) for running rabbitmq (in development), [Make](https://www.gnu.org/software/make/)

1. Clone this repository and create and activate a python virtual environment.
1. Inside a virtual environment or machine: `pip install -r requirements.txt`
1. Before first use, create the database by running `make migrate`
1. To start all of the services needed for the dev deployment run: `make serve-dev`

For development, also install and use the development tools:
1. `pip install -r requirements.dev.txt`
1. `pre-commit install`
