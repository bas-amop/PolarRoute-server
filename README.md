# PolarRoute Server

![Dev Status](https://img.shields.io/badge/Status-Active-green)
[![GitHub Tag](https://img.shields.io/github/v/tag/antarctica/PolarRoute-server?filter=v*.*.*&label=latest%20release)](https://github.com/antarctica/PolarRoute-server/tags)
[![GitHub License](https://img.shields.io/github/license/antarctica/PolarRoute-server)](https://github.com/antarctica/PolarRoute-server/blob/main/LICENSE)

A web server to manage requests for meshes and routes generated using the [PolarRoute](https://github.com/antarctica/PolarRoute) and [MeshiPhi](https://github.com/antarctica/MeshiPhi/) libraries,
implemented using Django, Celery and Django REST framework.

It currently takes *vessel* meshes created using MeshiPhi and serves requests for routes, which are calculated using PolarRoute.

## Setup/installation

PolarRouteServer can be installed from GitHub using `pip`.

+ Inside a virtual environment (e.g. venv, conda, etc.) run `pip install git+https://github.com/antarctica/PolarRoute-server`
  + To install a specific version append the tag, e.g. `pip intall git+https://github.com/antarctica/PolarRoute-server@v0.1.2`

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

#### Using docker compose

Optionally, use [docker compose](https://docs.docker.com/compose/install/) for development deployment to orchestrate celery and rabbitmq alongside the django development server.

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

### Configuration

Configuration of PolarRouteServer works with environment variables. You can either set these directly or from a `.env` file. An example `.env` file is included here as `env.example`.

Environment variables used directly by the Django site are prefixed wit `POLARROUTE_` and those which configure Celery are prefixed with `CELERY_`.

- `POLARROUTE_MESH_DIR` - absolute path to directory where mesh files and mesh metadata files will be made available (this location is periodically checked in production and new files ingested into the database based on the metadata file). A `UserWarning` is raised in production if this is not set.

The following are inherited from Django and more information can be found on their effects via the [Django docs](https://docs.djangoproject.com/en/5.1/ref/settings/).
- `POLARROUTE_DEBUG` - enables Django debug options, must be `False` in production (default: `False`)
- `POLARROUTE_SECRET_KEY` - secret hash used for cookie signing etc. Must be set in production. A random key is generated if one is not set.
- `DJANGO_SETTINGS_MODULE` - sets the settings envrionment. Options: `polarrouteserver.settings.{production,development,test}` (Default: `polarrroutesserver.settings.production`)
- `POLARROUTE_ALLOWED_HOSTS` - comma-separated (no spaces) list of IP addresses or hostnames allowed for the server.
- `POLARROUTE_CORS_ALLOWED_ORIGINS` -  comma-separated (no spaces) list of IP addresses allowed for Cross Origin Site Requests. (See [django-cors-headers](https://pypi.org/project/django-cors-headers/) on PyPI for more.)
- `CELERY_BROKER_URL` - URL for rabbitMQ message broker used by celery. (Default: `amqp://guest:guest@localhost`)
- `POLARROUTE_LOG_LEVEL` - sets the logging level from standard log level options: INFO, DEBUG, ERROR, WARNING etc. (Default: `INFO`)
- `POLARROUTE_LOG_DIR` - sets the output directory for logs. By default only used in production settings environment.


### Production Deployment
For production, the following are required:
+ Access to a RabbitMQ server, (can use `make start-rabbitmq` to start one in a docker container)
+ Celery and celery beat servers running,
+ WSGI server, e.g. Gunicorn.

For serving with Gunicorn, run `make start-django-server` to serve with WSGI and production settings.

### Management of a deployment

All of the commands used for administration of a Django project are available post-installation via the `django-admin` command.

Of particular interest in production are:

```shell
$ django-admin makemigrations # create new migrations files based on changes to models
$ django-admin migrate # apply new migrations files to alter the database
$ django-admin dbshell # open the database's command line interface
```

To see more commands, run `django-admin --help`.

In addition a custom command is available to manually insert new meshes into the database from file:

```shell
$ django-admin insert_mesh <Mesh file or list of files>
```

`insert_mesh` takes a filename or list of filepaths containing meshes either as `.vessel.json` format or gzipped vessel mesh files.

Only meshes which are not present in the database will be inserted. Uniqueness is based on the md5 hash of the unzipped vessel mesh file.

## Making requests using the demo tool

A demo script is available in this repo (`polarrouteserver/demo.py`) to be used as a utility for making route requests.

To obtain, either:
+ Clone this whole repo [as above](#for-development)
+ Download the file from its GitHub page here: https://github.com/antarctica/PolarRoute-server/blob/main/demo.py

This can be done with `wget` by running:

```
wget https://raw.githubusercontent.com/antarctica/PolarRoute-server/refs/heads/main/polarrouteserver/demo.py
```

To run, you'll just need python ~3.11 installed. Earlier versions of python may work, but are untested.

### Usage
Help for the utility can be printed out by running `python demo.py --help`.

Alternatively, if you have the package installed, a command named `request_route` is made available.

```sh
$ request_route --help
# OR
$ python demo.py --help

usage: demo.py [-h] [-u URL] -s [START] -e [END] [-d [DELAY]] [-f] [-o [OUTPUT]]

Requests a route from polarRouteServer, repeating the request for status until the route is available. Specify start and end points by coordinates or from one of the standard locations: ['bird', 'falklands',
'halley', 'rothera', 'kep', 'signy', 'nyalesund', 'harwich', 'rosyth']

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     Base URL to send request to.
  -s [START], --start [START]
                        Start location either as the name of a standard location or latitude,longitude separated by a comma, e.g. -56.7,-65.01
  -e [END], --end [END]
                        End location either as the name of a standard location or latitude,longitude separated by a comma, e.g. -56.7,-65.01
  -d [DELAY], --delay [DELAY]
                        (integer) number of seconds to delay between status calls.
  -f, --force           Force polarRouteServer to recalculate the route even if it is already available.
  -o [OUTPUT], --output [OUTPUT]
                        File path to write out route to. (Default: None and print to stdout)
```

So to request a route from Falklands to Rothera, for example:

```sh
python demo.py --url example-polar-route-server.com -s falklands -e rothera --delay 120 --output demo_output.json
```

This will request the route from the server running at `example-polar-route-server.com`, and initiate a route calculation if one is not already available.

The utility will then request the route's status every `120` seconds.

The HTTP response from each request will be printed to stdout.

Once the route is available it will be returned, or if 10 attempts to get the route have passed, the utility will stop.

