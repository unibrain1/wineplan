# Wine Plan

A personal wine cellar management system that generates a multi-year drinking plan from your [CellarTracker](https://www.cellartracker.com) inventory and pairs wines with your Google Calendar meal plan.

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│  FETCH (scripted)                                       │
│    CellarTracker inventory + Google Calendar menu        │
├─────────────────────────────────────────────────────────┤
│  GENERATE PLAN (scripted — rules-based)                 │
│    52-week plan: priority, season, evolution, holidays  │
├─────────────────────────────────────────────────────────┤
│  GENERATE NOTES (LLM — Claude Code CLI)                 │
│    Contextual tasting notes for each bottle              │
├─────────────────────────────────────────────────────────┤
│  COMPARE & PAIR (scripted)                              │
│    Inventory diff + food-wine pairing suggestions        │
├─────────────────────────────────────────────────────────┤
│  PUBLISH                                                │
│    Self-updating web app served via nginx                │
└─────────────────────────────────────────────────────────┘
```

The plan regenerates from scratch every run. CellarTracker is the system of record for all wine metadata. Claude generates tasting notes. Everything else is deterministic.

## Quick Start

### Prerequisites

- Python 3.12+
- [1Password CLI](https://developer.1password.com/docs/cli/) (`op`)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude`) — for tasting notes
- A CellarTracker account
- A Google Calendar with meal plans

### Setup

```bash
pip install -r requirements.txt
```

Create `.env`:
```
OP_SERVICE_ACCOUNT_TOKEN=<token>
USERNAME="op://<vault>/<item>/username"
PASSWORD="op://<vault>/<item>/password"
GOOGLE_CALENDAR_ICS_URL=https://calendar.google.com/calendar/ical/.../basic.ics
CLAUDE_CODE_OAUTH_TOKEN=<token from: claude setup-token>
```

### Run

```bash
bash fetch.sh
# Serve the site:
python3 -m http.server -d site 8080
```

### Docker (Homelab)

```bash
# Persistent service — syncs nightly + serves via nginx
docker compose up --build

# One-shot test run
docker compose run --rm run-now
```

Container: `wine-planner` on port `8080`. Schedule configurable via `SYNC_SCHEDULE` env var.

## The Sommelier

The pairing engine matches your meal plan against your cellar and suggests wines. Suggestions prioritize bottles that need drinking soon. See [Menu Guide](docs/menu-guide.md) for tips.

## Documentation

- [CLAUDE.md](CLAUDE.md) — Project conventions and pipeline architecture
- [docs/fetch.md](docs/fetch.md) — Plan criteria and rules reference
- [docs/menu-guide.md](docs/menu-guide.md) — How to write menu entries for best pairings
