#!/usr/bin/env bash
set -euo pipefail

echo "==> Starting wine plan service..."

# Self-update from git
git config --global --add safe.directory /app
echo "==> Pulling latest from git..."
git -C /app pull --ff-only 2>&1 || echo "WARNING: git pull failed — running with current version"

# Install/update Python dependencies if requirements changed
pip install --no-cache-dir --root-user-action=ignore -q -r /app/requirements.txt 2>&1 || true

# Link nginx config from the repo
ln -sf /app/nginx.conf /etc/nginx/sites-available/default

# Ensure data directory exists
mkdir -p /app/data

# Start nginx first so the site is available immediately
echo "==> Starting web server on port 8080..."
nginx

# Set up periodic sync with supercronic (runs as non-root)
SCHEDULE="${SYNC_SCHEDULE:-0 2 * * *}"
echo "${SCHEDULE} cd /app && bash fetch_docker.sh" > /tmp/crontab
echo "    Scheduled sync: ${SCHEDULE}"
supercronic /tmp/crontab &

# Run the pipeline once (site is already serving)
echo "==> Running initial sync..."
bash /app/fetch_docker.sh || echo "WARNING: Initial sync failed, serving stale plan"

echo "==> Ready."
tail -f /dev/null
