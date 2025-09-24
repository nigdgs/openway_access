#!/usr/bin/env bash
set -e

# Load env (optional; docker-compose already passes them)
: "${DJANGO_SETTINGS_MODULE:=accessproj.settings.dev}"
export DJANGO_SETTINGS_MODULE

./scripts/wait-for-db.sh

python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

# Run dev server (simpler than gunicorn for MVP)
python manage.py runserver 0.0.0.0:8000
