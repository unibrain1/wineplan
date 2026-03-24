# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal wine cellar management project. Maintains a multi-year wine drinking plan synchronized with a live CellarTracker inventory and a Google Calendar menu plan. A nightly pipeline generates a fresh plan, adds tasting notes via Claude, and publishes a web app.

## Pipeline Flow

```
SELF-UPDATE
  └── git pull (picks up code changes without rebuild)

FETCH (scripted, parallel)
  ├── CellarTracker inventory  → data/inventory.tsv → data/inventory.json
  ├── CellarTracker notes      → data/notes.tsv
  ├── CellarTracker food tags  → data/foodtags.tsv
  └── Google Calendar menu     → data/menu.ics → data/menu.json

GENERATE PLAN (scripted — rules-based) → data/plan.json (staging)

GENERATE NOTES (LLM — Claude Code CLI) → data/plan.json (augmented with CT notes)

COMPARE & PAIR (scripted)
  ├── inventory + plan → data/report.json
  └── menu + plan + inventory → data/pairing_suggestions.json

PUBLISH (atomic — site always has complete plan with notes)
  └── Copy plan.json + pairing_suggestions.json + report.json → site/
```

## Directory Structure

```
site/                         — Served by nginx (data + presentation + style separated)
  index.html                  — App shell (HTML structure + JS rendering logic)
  style.css                   — All CSS styles (Sandstone color scheme)
  plan.json                   — Plan data: allWeeks, quarterInfo, changelog (generated)
  pairing_suggestions.json    — Pairing suggestions (generated)
  report.json                 — Inventory diff report (generated)
scripts/
  plan_config.py              — Holidays + evolution tracks (gitignored, personal)
  plan_config.py.sample       — Template for plan_config.py
  wine_utils.py               — Shared: CURRENT_YEAR, TYPE_TO_BADGE, normalize, urgency_score
  generate_plan.py            — Deterministic plan generator (rules-based)
  generate_notes.py           — Tasting notes (Claude CLI, augmented with CT notes/food tags)
  wine_keywords.py            — Single source of truth for food keywords and pairing rules
  parse_inventory.py          — inventory.tsv → inventory.json
  parse_menu.py               — menu.ics → menu.json (Google Calendar .ics feed)
  compare.py                  — inventory.json + plan.json → report.json
  pairing.py                  — menu.json + plan.json + inventory.json → pairing_suggestions.json
docs/
  menu-guide.md               — How to write menu entries for best pairing results
data/                         — Staging area + generated artifacts (gitignored)
  plan.json                   — Staged plan (copied to site/ after notes generated)
  plan_previous.json          — Backup of previous live plan (for changelog diff)
pipeline.sh                   — Shared pipeline logic (sourced by fetch.sh and fetch_docker.sh)
fetch.sh                      — Local pipeline entry point
fetch_docker.sh               — Docker pipeline entry point
Dockerfile                    — Python 3.12 + nginx + 1Password + Claude CLI + supercronic + git
docker-compose.yml            — the-sommelier on port 8089 + Traefik proxy + run-now profile
entrypoint.sh                 — git pull, starts nginx, schedules cron, runs initial sync
nginx.conf                    — Serves site/ directory on port 8080 (non-root)
requirements.txt              — Python dependencies (icalendar)
.env                          — Secrets (gitignored)
.env.sample                   — Template for .env (no secrets)
```

## Running the Pipeline

```bash
bash fetch.sh
```

## Docker Deployment

Production runs on **docker02**. To restart or rebuild the running application, SSH to docker02:

```bash
# SSH to production host
ssh docker02

# First time or Dockerfile changes
docker compose up --build -d

# Code changes only (scripts, pipeline) — no rebuild needed
docker compose down && docker compose up -d

# One-shot test run
docker compose run --rm run-now
```

Container: `the-sommelier`. Runs as non-root (configurable UID/GID in compose). Uses supercronic.
Sync schedule configurable via `SYNC_SCHEDULE` env var (default: `0 2 * * *`).

Self-updating: container does `git pull` on startup and before each pipeline run.
Code changes pushed to GitHub are picked up automatically on next `down/up` or scheduled run.
`docker compose restart` does NOT re-run the entrypoint — use `down/up` instead.

## LLM vs Data Boundary

- **CellarTracker is the system of record** for all wine metadata: Type/badge, Varietal, Appellation, scores, drinking windows, quantity.
- **Scripted rules** handle: plan generation (scheduling, priority, seasonal fit, evolution, holidays), inventory comparison, food-wine pairing suggestions.
- **Claude (LLM)** handles: tasting note generation only. Notes are contextual 1-2 sentence descriptions augmented with CellarTracker notes and food tags. If Claude CLI is unavailable, the pipeline continues with empty notes.

## Architecture: Data / Presentation / Style

- **Data** — `site/plan.json`, `site/pairing_suggestions.json`, `site/report.json`. All JSON, all generated. Staged in `data/` first, copied to `site/` atomically after all steps complete.
- **Presentation** — `site/index.html`. App shell with JS rendering. Fetches JSON on load.
- **Style** — `site/style.css`. Sandstone color scheme (Bootswatch).

## plan.json Structure

Generated by `generate_plan.py`. Contains:
- `allWeeks`: 52 entries, one per week
- `quarterInfo`: seasonal section headers
- `changelog`: diff vs previous live plan (from `site/plan.json`)

All metadata (badge, appellation, window, score) comes from CellarTracker inventory.
Notes come from Claude (augmented with CT notes/food tags). Scheduling decisions come from rules.

## Plan Generation Rules

Implemented in `scripts/generate_plan.py`:
- Cadence: 1 bottle/week, 52 weeks, starting current Monday
- Priority: past peak → expiring → peak window → entering window → long-agers (held)
- Long-ager hold: BeginConsume > current_year + 2, or hold back 2 if 3+ bottles
- Seasonal: sparkling/rosé/white for spring-summer, bold reds for fall-winter
- Evolution tracks and holidays configured in `scripts/plan_config.py` (gitignored, personal data)
- Sample at `scripts/plan_config.py.sample`

## CellarTracker Data Sources

- `Table=Inventory` — bottles, varietals, types, scores, windows (system of record)
- `Table=Notes` — user's tasting notes (augments Claude-generated notes)
- `Table=FoodTags` — user's food pairing tags (augments pairing suggestions)
- Community tasting notes are NOT available via the export API

## Google Calendar Integration

- Menu data from Paprika-managed calendar via secret .ics URL
- `GOOGLE_CALENDAR_ICS_URL` in `.env`
- UTC timestamps converted to Pacific time (`America/Los_Angeles`)
- Keywords extracted using `wine_keywords.py`

## Wine-Food Pairing Engine ("The Sommelier")

- `wine_keywords.py`: single source of truth for keywords and pairing rules
- Three outcomes: Pairs Well (green), Sommelier Pick (blue), No Match (muted)
- Suggestions prioritize urgent bottles in their drinking window
- Each meal gets a unique suggestion
- Varietal-aware: looks up inventory varietal for planned wines to improve matching

## Deployment Gotchas

- Shell scripts must have executable permission in git: `chmod +x *.sh && git add`
- Docker volume mount requires `git config --global --add safe.directory /app` (handled in entrypoint)
- Pre-commit hooks (ruff format) may modify files on first commit — re-stage and commit again

## Important Conventions

- Weeks begin on Monday
- Pairing scores: `"good"`, `"partial"`, `"poor"`, `"neutral"`
- `pipeline.sh` has all shared logic; `fetch.sh` and `fetch_docker.sh` are thin wrappers
- Plan is regenerated from scratch every pipeline run — no manual editing of `plan.json`
- Plan staged to `data/plan.json`, only published to `site/` when complete with notes
- Shared utilities in `scripts/wine_utils.py` — do not duplicate `urgency_score`, `normalize`, `TYPE_TO_BADGE`, or `CURRENT_YEAR` in individual scripts
