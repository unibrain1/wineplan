#!/usr/bin/env bash
# Shared pipeline logic — sourced by fetch.sh and fetch_docker.sh
# Expects: working directory set to project root, env vars already loaded

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# --- FETCH (scripted) ---
log "==> Resolving credentials from 1Password..."
CT_USERNAME=$(op read "$USERNAME") || { log "ERROR: Failed to resolve CellarTracker username from 1Password"; exit 1; }
CT_PASSWORD=$(op read "$PASSWORD") || { log "ERROR: Failed to resolve CellarTracker password from 1Password"; exit 1; }

log "==> Fetching inventory and menu..."
curl -sf "https://www.cellartracker.com/xlquery.asp?User=${CT_USERNAME}&Password=${CT_PASSWORD}&Table=Inventory&Format=tab&Location=1" \
  -o data/inventory.tsv &
PID_CT=$!

curl -sf "${GOOGLE_CALENDAR_ICS_URL}" -o data/menu.ics &
PID_CAL=$!

wait $PID_CT || { log "ERROR: CellarTracker fetch failed — check credentials or network"; exit 1; }
wait $PID_CAL || { log "ERROR: Google Calendar fetch failed — check GOOGLE_CALENDAR_ICS_URL"; exit 1; }

LINES=$(wc -l < data/inventory.tsv | tr -d ' ')
log "    Downloaded $((LINES - 1)) bottles + menu calendar"

# --- PARSE (scripted) ---
log "==> Parsing inventory and menu..."
python3 scripts/parse_inventory.py data/inventory.tsv > data/inventory.json &
PID_INV=$!

python3 scripts/parse_menu.py data/menu.ics > data/menu.json &
PID_MENU=$!

wait $PID_INV || { log "ERROR: Inventory parse failed"; exit 1; }
wait $PID_MENU || { log "ERROR: Menu parse failed"; exit 1; }

# --- GENERATE PLAN (scripted — rules-based) ---
log "==> Generating plan..."
python3 scripts/generate_plan.py data/inventory.json site/plan.json || { log "ERROR: Plan generation failed"; exit 1; }

# --- GENERATE NOTES (LLM — Claude Code CLI) ---
if command -v claude &> /dev/null; then
  log "==> Generating tasting notes (Claude)..."
  python3 scripts/generate_notes.py site/plan.json || log "WARNING: Note generation failed — plan will have empty notes"
else
  log "    Skipping note generation — claude CLI not available"
fi

# --- COMPARE & PAIR (scripted) ---
log "==> Comparing inventory vs plan..."
python3 scripts/compare.py data/inventory.json site/plan.json > data/report.json || { log "ERROR: Compare failed"; exit 1; }

log "==> Generating pairing suggestions..."
python3 scripts/pairing.py data/menu.json site/plan.json data/inventory.json > data/pairing_suggestions.json || { log "ERROR: Pairing failed"; exit 1; }

# --- PUBLISH (scripted) ---
log "==> Publishing to site/..."
cp data/pairing_suggestions.json site/pairing_suggestions.json
cp data/report.json site/report.json

log "==> Sync complete."
