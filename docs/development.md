# Development

Depends on:

* Python >=3.11
* [docker](https://docs.docker.com/get-docker/) for running rabbitmq
* [Make](https://www.gnu.org/software/make/)

<br>

1. Clone the repository and create and activate a python virtual environment of your choice.
1. Inside a virtual environment or machine: `pip install -e .[dev]`
1. Before first use, create the database by running `make migrate`
1. To start all of the services needed for the dev deployment run: `make serve-dev` (which sets the `DJANGO_SETTINGS_MODULE` environment variable and spins up celery, rabbitmq in a docker container, and the Django development server)

For development, also install and use the development tools with `pre-commit install`

A number of helpful development tools are made available through the `Makefile`, to see a description of each of these commands, run `make` (with no arguments) from the top-level of this directory.

## Release/Versioning

Version numbers should be used in tagging commits on the `main` branch and reflected in the `pyproject.toml` file and should be of the form `v0.1.7` using the semantic versioning convention.

## Making changes to the API

The API is documented in `./docs/apischema.yml` using the OpenAPI 3.0 standard (formerly known as swagger).

Any changes to the Web API should be **manually** reflected in the schema. These can be checked by building the docs and checking the [API reference page](api.md) or serving using swagger (`make start-swagger`).
