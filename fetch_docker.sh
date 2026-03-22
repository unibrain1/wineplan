#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# In Docker, env vars come from docker-compose env_file.
# Locally, source .env if it exists.
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

source pipeline.sh

echo "==> Done."
jq '.summary' data/report.json
echo ""
echo "Pairing summary:"
jq '{total_meals, matched_weeks, sommelier_picks}' data/pairing_suggestions.json
