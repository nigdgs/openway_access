#!/usr/bin/env bash
# Simple wait-for DB using pg_isready
set -e
HOST="${DB_HOST:-db}"
PORT="${DB_PORT:-5432}"

echo "Waiting for Postgres at ${HOST}:${PORT}..."
until pg_isready -h "${HOST}" -p "${PORT}" >/dev/null 2>&1; do
  sleep 1
done
echo "Postgres is ready."