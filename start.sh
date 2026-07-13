#!/usr/bin/env bash
# Démarrage du conteneur : migrations + données de démo, puis gunicorn.
set -o errexit

python manage.py migrate --no-input
python manage.py seed_demo

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
