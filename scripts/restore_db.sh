#!/bin/sh
# Restore pre-seeded database dump (weather + AOD baseline).
# Usage: docker compose exec -T db sh -c "$(cat scripts/restore_db.sh)"
set -e
gunzip -c /docker-entrypoint-initdb.d/seed_data.sql.gz | psql -h localhost -U aoduser -d aodproject
echo "Database restored from seed_data.sql.gz"
