#!/usr/bin/env bash
# Shared pipeline logic — sourced by fetch.sh and fetch_docker.sh
# Expects: working directory set to project root, .env already loaded

echo "==> Resolving credentials from 1Password..."
CT_USERNAME=$(op read "$USERNAME")
CT_PASSWORD=$(op read "$PASSWORD")

echo "==> Fetching inventory and menu..."
curl -sf "https://www.cellartracker.com/xlquery.asp?User=${CT_USERNAME}&Password=${CT_PASSWORD}&Table=Inventory&Format=tab&Location=1" \
  -o data/inventory.tsv &
PID_CT=$!

curl -sf "${GOOGLE_CALENDAR_ICS_URL}" -o data/menu.ics &
PID_CAL=$!

wait $PID_CT || { echo "ERROR: CellarTracker fetch failed"; exit 1; }
wait $PID_CAL || { echo "ERROR: Calendar fetch failed"; exit 1; }

LINES=$(wc -l < data/inventory.tsv | tr -d ' ')
echo "    Downloaded $((LINES - 1)) bottles + menu calendar"

echo "==> Parsing inventory and plan..."
python3 scripts/parse_inventory.py data/inventory.tsv > data/inventory.json &
PID_INV=$!

python3 scripts/parse_plan.py site/index.html > data/plan.json &
PID_PLAN=$!

wait $PID_INV || { echo "ERROR: Inventory parse failed"; exit 1; }
wait $PID_PLAN || { echo "ERROR: Plan parse failed"; exit 1; }

echo "==> Parsing menu..."
python3 scripts/parse_menu.py data/menu.ics > data/menu.json

echo "==> Comparing inventory vs plan..."
python3 scripts/compare.py data/inventory.json data/plan.json > data/report.json

echo "==> Generating pairing suggestions..."
python3 scripts/pairing.py data/menu.json data/plan.json data/inventory.json > data/pairing_suggestions.json

echo "==> Validating plan against inventory..."
python3 scripts/validate_plan.py data/inventory.json site/index.html

echo "==> Injecting pairings into site..."
python3 scripts/inject_pairings.py data/pairing_suggestions.json site/index.html
cp data/report.json site/report.json
