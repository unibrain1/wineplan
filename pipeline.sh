#!/usr/bin/env bash
set -euo pipefail
# Shared pipeline logic — sourced by fetch.sh and fetch_docker.sh
# Expects: working directory set to project root, env vars already loaded

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# --- SELF-UPDATE ---
if [ -d .git ]; then
  log "==> Pulling latest from git..."
  git pull --ff-only 2>&1 || log "WARNING: git pull failed — running with current version"
fi

# --- FETCH (scripted) ---
log "==> Resolving credentials from 1Password..."
CT_USERNAME=$(op read "$USERNAME") || { log "ERROR: Failed to resolve CellarTracker username from 1Password"; exit 1; }
CT_PASSWORD=$(op read "$PASSWORD") || { log "ERROR: Failed to resolve CellarTracker password from 1Password"; exit 1; }

CT_BASE="https://www.cellartracker.com/xlquery.asp?User=${CT_USERNAME}&Password=${CT_PASSWORD}&Format=tab"

log "==> Fetching inventory, notes, food tags, and menu..."
curl -sf "${CT_BASE}&Table=Inventory&Location=1" -o data/inventory.tsv &
PID_CT=$!

curl -sf "${CT_BASE}&Table=Notes" -o data/notes.tsv &
PID_NOTES=$!

curl -sf "${CT_BASE}&Table=FoodTags" -o data/foodtags.tsv &
PID_FOOD=$!

curl -sf "${GOOGLE_CALENDAR_ICS_URL}" -o data/menu.ics &
PID_CAL=$!

wait $PID_CT || { log "ERROR: CellarTracker inventory fetch failed"; exit 1; }
wait $PID_NOTES || { log "WARNING: CellarTracker notes fetch failed — continuing without notes"; }
wait $PID_FOOD || { log "WARNING: CellarTracker food tags fetch failed — continuing without food tags"; }
wait $PID_CAL || { log "ERROR: Google Calendar fetch failed — check GOOGLE_CALENDAR_ICS_URL"; exit 1; }

LINES=$(wc -l < data/inventory.tsv | tr -d ' ')
log "    Downloaded $((LINES - 1)) bottles + notes + food tags + menu calendar"

# --- PARSE (scripted) ---
log "==> Parsing inventory and menu..."
python3 scripts/parse_inventory.py data/inventory.tsv > data/inventory.json &
PID_INV=$!

python3 scripts/parse_menu.py data/menu.ics > data/menu.json &
PID_MENU=$!

wait $PID_INV || { log "ERROR: Inventory parse failed"; exit 1; }
wait $PID_MENU || { log "ERROR: Menu parse failed"; exit 1; }

# --- GENERATE PLAN to staging (scripted — rules-based) ---
# Build new plan in data/ first, only publish to site/ when complete with notes
log "==> Generating plan..."
python3 scripts/generate_plan.py data/inventory.json data/plan.json || { log "ERROR: Plan generation failed"; exit 1; }

# --- GENERATE NOTES (LLM — Claude Code CLI, augmented with CT notes) ---
if command -v claude &> /dev/null; then
  log "==> Generating tasting notes (Claude)..."
  python3 scripts/generate_notes.py data/plan.json data/notes.tsv data/foodtags.tsv || log "WARNING: Note generation failed — plan will have empty notes"
else
  log "    Skipping note generation — claude CLI not available"
fi

# --- COMPARE & PAIR (scripted) ---
log "==> Comparing inventory vs plan..."
python3 scripts/compare.py data/inventory.json data/plan.json > data/report.json || { log "ERROR: Compare failed"; exit 1; }

log "==> Generating pairing suggestions..."
python3 scripts/pairing.py data/menu.json data/plan.json data/inventory.json > data/pairing_suggestions.json || { log "ERROR: Pairing failed"; exit 1; }

# --- PUBLISH atomically (site always has a complete plan with notes) ---
log "==> Publishing to site/..."
cp data/plan.json site/plan.json
cp data/pairing_suggestions.json site/pairing_suggestions.json
cp data/report.json site/report.json

log "==> Sync complete."
