# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal wine cellar management project. Maintains a multi-year wine drinking plan synchronized with a live CellarTracker inventory and a Google Calendar menu plan. A nightly pipeline fetches data, generates food-wine pairing suggestions ("The Sommelier"), and publishes the plan as a self-contained HTML page.

## Directory Structure

```
site/
  index.html              — The wine plan (self-contained HTML/CSS/JS, Sandstone color scheme)
scripts/
  wine_keywords.py        — Single source of truth for food keywords and pairing rules
  parse_inventory.py      — inventory.tsv → inventory.json
  parse_plan.py           — site/index.html → plan.json
  parse_menu.py           — menu.ics → menu.json (Google Calendar .ics feed)
  compare.py              — inventory.json + plan.json → report.json
  pairing.py              — menu.json + plan.json + inventory.json → pairing_suggestions.json
  inject_pairings.py      — Embeds pairing data into site/index.html (replaces PAIRING_PLACEHOLDER)
docs/
  fetch.md                — Task instructions for the full inventory sync workflow
  menu-guide.md           — How to write menu entries for best pairing results
data/                     — Generated artifacts (gitignored)
pipeline.sh               — Shared pipeline logic (sourced by fetch.sh and fetch_docker.sh)
fetch.sh                  — Local pipeline entry point (dev/testing)
fetch_docker.sh           — Docker pipeline entry point (copies output to nginx web root)
Dockerfile                — Python 3.12 + nginx + 1Password CLI + cron
docker-compose.yml        — Runs the container on port 8080
entrypoint.sh             — Runs sync at startup, schedules nightly cron at 2 AM, starts nginx
nginx.conf                — Serves site/ directory
requirements.txt          — Python dependencies (icalendar)
.env                      — OP_SERVICE_ACCOUNT_TOKEN, 1Password secret refs, GOOGLE_CALENDAR_ICS_URL
```

## Running the Pipeline

```bash
bash fetch.sh
```

The pipeline (defined in `pipeline.sh`):
1. Resolves CellarTracker credentials from 1Password
2. Fetches inventory + menu calendar in parallel
3. Parses inventory + plan in parallel
4. Parses menu, compares inventory vs plan, generates pairing suggestions
5. Injects pairing data into `site/index.html`

All generated data lands in `data/`. The final HTML is self-contained and can be opened directly in a browser.

After the pipeline runs, review `data/report.json` and present findings to the user. Plan regeneration (Step 3 in fetch.md) is the only step requiring LLM judgment.

## Docker Deployment

```bash
docker compose up --build
```

Runs the pipeline at startup and nightly at 2 AM. Serves the plan at `http://<host>:8080`.

## Architecture of site/index.html

- Pure vanilla HTML/CSS/JS — no build step, no dependencies, no framework.
- Color scheme follows Bootswatch Sandstone palette (primary #325d88, warm sand backgrounds).
- Fonts loaded from Google Fonts (Playfair Display, DM Sans).
- SVG wine glass icons distinguish wine types (champagne flute for sparkling, varying fill levels for rosé/white/red).
- `allWeeks` array: each entry is a flat object with fields: `week`, `year`, `date`, `season`, `badge`, `vintage`, `name`, `appellation`, `window`, `score`, `urgent`, `special`, `evolution`, `occasion`, `note`.
- `pairingSuggestions` array: injected by `inject_pairings.py` at the `PAIRING_PLACEHOLDER` marker. Each entry has: `date`, `meal`, `keywords`, `planned_wine`, `planned_badge`, `pairing` (score/details), and optionally `suggested_bottle` with a specific bottle from inventory.
- `changelog` object: tracks what changed in the most recent plan sync. Rendered in the "What Changed" tab.
- Five tabs: Year 1, Year 2, All 104 Weeks, Monthly Calendar, What Changed.
- Weeks begin on Monday.
- Legend explains wine type icons, tile border colors (urgent/special/evolution), and pairing indicators (pairs well / sommelier pick / no match).
- Rendering logic builds month-grouped views from `allWeeks`, with filtering and search applied client-side.

## Google Calendar Integration

- Menu data comes from a Paprika-managed calendar via a secret .ics URL.
- The URL is stored in `.env` as `GOOGLE_CALENDAR_ICS_URL`.
- `parse_menu.py` converts UTC timestamps to Pacific time (`America/Los_Angeles`) and includes meals from the current week's Monday through a 2-year horizon.
- Keywords are extracted from both the event summary and description using the canonical list in `wine_keywords.py`.

## Wine-Food Pairing Engine ("The Sommelier")

- `wine_keywords.py` is the single source of truth for food keywords and their pairing rules, used by both `parse_menu.py` (extraction) and `pairing.py` (scoring).
- `pairing.py` scores planned wines against menu keywords. Three outcomes displayed on cards:
  - **Pairs Well** (green) — planned wine matches the meal
  - **Sommelier Pick** (blue) — suggests a specific bottle from the cellar
  - **No Match** (muted) — no food keywords matched, enjoy the planned wine
- Bottle suggestions use the priority rules: past peak → expiring this year → expiring next year → peak window.
- Only bottles in their drinking window (BeginConsume ≤ current year + 1) are suggested.
- Bottles already planned for later weeks can be suggested to move forward.
- Each meal gets a unique suggestion — the engine avoids recommending the same bottle twice.
- Pairing data is embedded directly in the HTML (not fetched via AJAX) so the file works when opened from the filesystem.

## CellarTracker Integration

- **CellarTracker is the system of record for all wine metadata.** Type, badge, varietal, appellation, scores, drinking windows — all come from CellarTracker, never inferred or guessed by the LLM.
- Export API endpoint: `https://www.cellartracker.com/xlquery.asp` with query params `User`, `Password`, `Table=Inventory`, `Format=tab`, `Location=1`.
- Returns tab-delimited text (one row per physical bottle). Key fields: Vintage, Wine, Varietal, Type, Country, Region, SubRegion, Appellation, iWine, Quantity (derived by counting rows per iWine), Location, Bin, Size, BeginConsume, EndConsume, CT, MY.
- `validate_plan.py` runs each pipeline cycle to cross-reference plan badges against CellarTracker's `Type` field and auto-correct mismatches.
- **Credentials must never be written to any file.** They are resolved at runtime from 1Password via `op read` using secret references in `.env`.

## LLM vs Data Boundary

- **CellarTracker provides:** wine metadata (Type/badge, Varietal, Appellation, scores, drinking windows, quantity)
- **The LLM provides:** scheduling decisions (which bottle in which week, seasonal fit, urgency ordering, pairing suggestions)
- The LLM must never invent or override wine metadata. If a field is available in inventory.json, use it.

## Important Conventions

- When matching inventory bottles to plan entries, match on vintage year + wine name (fuzzy, with alias expansion — see `compare.py` ALIASES dict).
- Drinking window urgency: bottles past `EndConsume` or within 1 year of it are considered urgent.
- Any plan updates should preserve the existing HTML structure, `allWeeks` data format, and update the `changelog` object.
- Pairing scores are string constants: `"good"`, `"partial"`, `"poor"`, `"neutral"` — used across Python and JS.
- `pipeline.sh` contains all shared pipeline logic. `fetch.sh` and `fetch_docker.sh` are thin wrappers.
