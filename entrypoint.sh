#!/usr/bin/env bash
set -euo pipefail

echo "==> Starting wine plan service..."

# Start nginx first so the site is available immediately (serves from /app/site via volume mount)
echo "==> Starting web server on port 80..."
nginx

# Set up periodic sync (default: 2:00 AM daily, configurable via SYNC_SCHEDULE env var)
SCHEDULE="${SYNC_SCHEDULE:-0 2 * * *}"
echo "${SCHEDULE} cd /app && bash fetch_docker.sh >> /proc/1/fd/1 2>&1" | crontab -
echo "    Scheduled sync: ${SCHEDULE}"
service cron start

# Run the pipeline once (site is already serving)
echo "==> Running initial sync..."
bash /app/fetch_docker.sh || echo "WARNING: Initial sync failed, serving stale plan"

# Keep the container running (nginx is already running as daemon)
echo "==> Ready."
tail -f /dev/null
