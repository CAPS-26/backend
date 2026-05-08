#!/bin/sh
set -e

if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running Database Migrations..."
    alembic upgrade head || exit 1

    echo "Running Data Seeding (Baseline)..."
    python scripts/seed.py stations || echo "Seed stations skipped or failed"
fi

echo "Starting Application..."
exec "$@"
