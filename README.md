# PolarRoute Server

**Project status**: Under active development.

A web server to manage requests for meshes and routes generated using the PolarRoute and MeshiPhi libraries,
implemented using Django, Celery and Django REST framework.

## Setup/installation

PolarRouteServer can be installed from GitHub using `pip`.

1. Inside a virtual environment (e.g. venv, conda, etc.) run `pip install git+https://github.com/antarctica/PolarRoute-server`

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

### Configuration

Configuration may either be achieved with config files or environment variables.


To deploy with development or production settings a corresponding `development.yaml` or `production.yaml` file can be present in the `config/` directory.

In the `config/` directory you will find a template config file, `template.yaml`, the deployment config file should match the fields in the template.

Alternatively, set the appropriate environment variables.

Below the names of `ENVIRONMENT_VARIABLES` and equivalent keys in yaml config files are listed.

- `POLARROUTE_MESH_DIR`/"mesh_dir" - absolute path to directory where mesh files and mesh metadata files will be made available (this location is periodically checked in production and new files ingested into the database based on the metadata file)
- `POLARROUTE_ALLOWED_HOSTS`/"allowed_hosts" - list/array of IP addresses or hostnames allowed for the server.

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

To run, you'll just need python 3.11 installed.

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

