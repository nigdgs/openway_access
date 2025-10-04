#!/usr/bin/env bash
set -e

# Default to dev if not specified
: "${DJANGO_SETTINGS_MODULE:=accessproj.settings.dev}"

./scripts/wait-for-db.sh

python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

# Conditional server startup based on environment
if [[ "$DJANGO_SETTINGS_MODULE" == *"prod"* ]]; then
    echo "Starting production server with Gunicorn..."
    exec gunicorn accessproj.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 4 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -
elif [[ "$DJANGO_SETTINGS_MODULE" == *"test"* ]]; then
    echo "Test environment detected, running tests..."
    exec python manage.py test
else
    echo "Starting development server..."
    exec python manage.py runserver 0.0.0.0:8000
fi