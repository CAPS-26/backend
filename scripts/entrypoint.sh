#!/bin/sh
set -e

echo "Running Database Migrations..."
alembic upgrade head

echo "Running Data Seeding (Baseline)..."
python scripts/seed.py

echo "Starting Application..."
exec "$@"
