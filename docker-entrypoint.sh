#!/bin/bash

set -e

env

python manage.py migrate
python manage.py ensure_adminuser --no-input
python manage.py loaddata locations_bas.json

exec "$@"