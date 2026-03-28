#!/usr/bin/env bash
set -e

echo "[backend] Waiting for Postgres at ${DB_HOST}:${DB_PORT}..."
until nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done

echo "[backend] Applying migrations..."
python manage.py migrate --noinput

echo "[backend] Collecting static files..."
python manage.py collectstatic --noinput

#echo "[backend] Starting Django dev server..."
#python manage.py runserver 0.0.0.0:8000

echo "[backend] Starting Gunicorn..."
gunicorn flinggolf_backend.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60
