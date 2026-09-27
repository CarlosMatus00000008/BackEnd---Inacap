#!/usr/bin/env bash
# Script que Render ejecuta en cada despliegue.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
