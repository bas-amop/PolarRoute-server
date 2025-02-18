# PolarRoute-Server

![Dev Status](https://img.shields.io/badge/Status-Active-green)
[![GitHub Tag](https://img.shields.io/github/v/tag/bas-amop/PolarRoute-server?filter=v*.*.*&label=latest%20release)](https://github.com/bas-amop/PolarRoute-server/tags)
[![GitHub License](https://img.shields.io/github/license/bas-amop/PolarRoute-server)](https://github.com/bas-amop/PolarRoute-server/blob/main/LICENSE)
![](coverage.svg)

A web server to manage requests for meshes and routes generated using the [PolarRoute](https://github.com/bas-amop/PolarRoute) and [MeshiPhi](https://github.com/bas-amop/MeshiPhi/) libraries,
implemented using Django, Celery and Django REST framework.

It currently takes *vessel* meshes created using MeshiPhi and serves requests for routes, which are calculated using PolarRoute.

## Setup/installation

PolarRouteServer can be installed from GitHub using `pip`.

+ Inside a virtual environment (e.g. venv, conda, etc.) run `pip install git+https://github.com/bas-amop/PolarRoute-server`
  + To install a specific version append the tag, e.g. `pip intall git+https://github.com/bas-amop/PolarRoute-server@v0.1.2`

Alternatively, clone this repository and install from source with `pip install -e .`

### For development

Depends on:
+ python >=3.11
+ [docker](https://docs.docker.com/get-docker/) for running rabbitmq (in development)
+ [Make](https://www.gnu.org/software/make/)

1. Clone this repository and create and activate a python virtual environment of your choice.
1. Inside a virtual environment or machine: `pip install -e .[dev]`
1. Before first use, create the database by running `make migrate`
1. To start all of the services needed for the dev deployment run: `make serve-dev` (which sets the `DJANGO_SETTINGS_MODULE` environment variable and spins up celery, rabbitmq in a docker container, and the Django development server)

For development, also install and use the development tools:
1. `pre-commit install`

A number of helpful development tools are made available through the `Makefile`, to see a description of each of these commands, run `make` (with no arguments) from the top-level of this directory.

#### Using docker compose (recommended)

Use [docker compose](https://docs.docker.com/compose/install/) for development deployment to orchestrate celery and rabbitmq alongside the django development server.

Clone this repository and run `docker compose up` to build and start the services.

**Note**: In development, meshes are not automatically ingested into the database. Follow these steps to add a mesh to the database.

1. Make a local directory structure with `mkdir -p data/mesh` and copy a vessel mesh file from MeshiPhi into `./data/mesh`, which is bind-mounted into the app container.
1. Run `docker compose exec app /bin/bash` to open a shell inside the running app container.
2. Run `django-admin insert_mesh /usr/src/app/data/mesh/<MESH FILENAME>` to insert the mesh into the database manually.

Test that the app is working using the demo tool [as described below](#making-requests-using-the-demo-tool). The URL of the service should be `localhost:8000`.

The django development server supports hot reloading and the source code is bind-mounted into the container, so changes should be reflected in the running app. Any changes to `polarrouteserver.route_api.models.py` will necessitate a migration to the database. To create and run migrations, run:

```
docker compose exec app django-admin makemigrations
docker compose exec app django-admin migrate
```

Optionally, Swagger can be used to serve an API schema. This is not started by default, but can be enabled by started `docker compose` with the `--profile swagger` option, e.g. `docker compose --profile swagger up -d` - the swagger UI will be served at `localhost:80/swagger`.
