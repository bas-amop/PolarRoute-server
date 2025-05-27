# Development

Depends on:

* Python >=3.11
* [docker](https://docs.docker.com/get-docker/) for running rabbitmq
* [Make](https://www.gnu.org/software/make/)

<br>

1. Clone the repository and create and activate a python virtual environment of your choice.
1. Inside a virtual environment or machine: `pip install -e .[dev]`
1. Make sure you have a running instance of the database, by running `docker compose up`, if it is not running already.
1. Before first use, create the database by running `make migrate`
1. To start all of the services needed for the dev deployment run: `make serve-dev` (which sets the `DJANGO_SETTINGS_MODULE` environment variable and spins up celery, rabbitmq in a docker container, and the Django development server)

For development, also install and use the development tools with `pre-commit install`

A number of helpful development tools are made available through the `Makefile`, to see a description of each of these commands, run `make` (with no arguments) from the top-level of this directory.

## Release/Versioning

Version numbers should be used in tagging commits on the `main` branch and reflected in the `pyproject.toml` file and should be of the form `v0.1.7` using the semantic versioning convention.

## Building & deploying the documentation

Run `make build-docs` to build the docs to the `./site` directory.

Then run `make deploy-docs` to deploy to the `gh-pages` branch of the repository. You must have write access to the repo.

## Making changes to the API

The API is documented in `./docs/apischema.yml` using the OpenAPI 3.0 standard (formerly known as swagger).

Any changes to the Web API should be **manually** reflected in the schema. These can be checked by building the docs and checking the [API reference page](api.md) or serving using swagger (`make start-swagger`).

## Docker containers and compose configuration
PolarRoute-server relies on four different services, orchestrated by [docker compose](https://docs.docker.com/compose/install/), to each be running in their own docker container.

As a user, you run a single `docker compose up` command to build and start these services.

As a developer, it is useful to be aware of what exactly these containers are doing.

Pre-fixed by `polarroute-server-`, the four services/containers are:
* `db-*`: a PostgreSQL database.
* `rabbitmq-*`: RabbitMQ.
* `celery-*`: Celery.
* `app-*`: The Django server running PolarRoute-server's route API.

Certain actions may rely on just a single service to be running, for example `make migrate` requires `polarroute-server-db-1` to be running. However, in practice, you will always be running all four containers at the same time.

Configurations for `docker compose up`'s execution are set in `compose.yml`.
