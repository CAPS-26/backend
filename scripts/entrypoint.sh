#!/bin/sh
set -e

echo "Running Database Migrations..."
alembic upgrade head || exit 1

echo "Running Data Seeding (Baseline)..."
# Jalankan seed hanya untuk stations agar stabil, tambahkan || true agar tidak menggagalkan deployment jika record sudah ada atau koneksi timeout
python scripts/seed.py stations || echo "Seed stations skipped or failed"

echo "Starting Application..."
exec "$@"
