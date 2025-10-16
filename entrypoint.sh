#!/bin/bash

set -e

python manage.py migrate

python manage.py loaddata locations_bas.json
python manage.py loaddata vehicles.json

exec "$@"