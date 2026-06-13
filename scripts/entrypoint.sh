#!/bin/sh
set -e

# Ensure data directories exist (needed for JAXA FTP downloads)
mkdir -p /app/data/Himawari /app/data/VIIRS /app/media

if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running Database Migrations..."
    alembic upgrade head || exit 1

    echo "Seeding stations baseline..."
    python scripts/seed.py stations || echo "Seed stations skipped or failed"

    echo "Restoring pre-seeded data (weather, AOD, PM2.5)..."
    python scripts/restore_seed.py || echo "Seed restore skipped or failed"
fi

echo "Starting Application..."
exec "$@"
