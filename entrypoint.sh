#!/bin/bash

set -e

python manage.py migrate

python manage.py loaddata locations_bas.json

exec "$@"