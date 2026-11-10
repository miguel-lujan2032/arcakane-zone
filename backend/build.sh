#!/usr/bin/env bash
# Script de construcción para Render.
# Render lo ejecuta automáticamente en cada deploy.
set -o errexit  # aborta si cualquier comando falla

pip install -r requirements.txt
python manage.py migrate
