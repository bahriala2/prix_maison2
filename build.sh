#!/usr/bin/env bash
# Script de build pour Render (ou tout hébergeur compatible).
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
# Crée les comptes et données de démonstration au premier déploiement (idempotent)
python manage.py seed_demo
