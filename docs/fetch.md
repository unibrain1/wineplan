# Update Wine Drinking Plan from CellarTracker

Fetch my live CellarTracker inventory, compare it against the current drinking plan, and offer to regenerate it.

---

## Step 1 — Fetch, Parse, and Compare

Run the pipeline script:

```bash
bash fetch.sh
```

This does everything deterministically (pipeline logic lives in `pipeline.sh`):

1. Loads `.env` (OP_SERVICE_ACCOUNT_TOKEN, secret references, GOOGLE_CALENDAR_ICS_URL)
2. Resolves CellarTracker credentials via `op read`
3. Fetches inventory + menu calendar in parallel → `data/inventory.tsv`, `data/menu.ics`
4. Parses inventory + menu in parallel → `data/inventory.json`, `data/menu.json`
5. Compares inventory vs `site/plan.json` → `data/report.json`
6. Generates pairing suggestions → `data/pairing_suggestions.json`
7. Validates plan badges against CellarTracker Type field (auto-corrects `site/plan.json`)
8. Copies `pairing_suggestions.json` and `report.json` to `site/`

Do not ask for credentials — they come from 1Password via `.env`. Do not write resolved credentials to any file.

---

## Step 2 — Review Report

Read `data/report.json` and `data/pairing_suggestions.json`, then present to the user:

**Inventory report** (`data/report.json`):
1. **Consumed** — bottles in the plan but no longer in inventory
2. **Urgent new** — in inventory, not in plan, `EndConsume` ≤ current year + 1
3. **Quantity mismatches** — plan count differs from inventory count
4. **Unplanned** — in inventory but not scheduled anywhere

**Pairing suggestions** (`data/pairing_suggestions.json`):
- For each upcoming menu item, shows whether the planned wine pairs well
- When it doesn't, The Sommelier suggests a specific bottle from the cellar (prioritized by urgency)
- Bottles already planned for later weeks can be moved forward
- Each meal gets a unique suggestion — no bottle is recommended twice

Ask the user to confirm before proceeding to Step 3.

---

## Step 3 — Regenerate Plan

When confirmed, rebuild `site/plan.json` using the criteria below. **Do not modify `site/index.html`** — it is a presentation shell. Only `site/plan.json` contains plan data.

All wine metadata (badge, varietal, appellation, scores, windows) must come from `data/inventory.json` (CellarTracker is the system of record). The LLM decides scheduling only.

---

## Plan Criteria

These rules govern how bottles are scheduled. Update this section if the criteria change.

### Cadence

- One bottle per week
- Weeks begin on Monday
- Starting week: Monday of the current week
- One-year rolling horizon (52 weeks)

### People & Context

- Drinking with a partner/spouse most nights
- ~24 new bottles arrive annually from Dion Vineyard, Domaine Drouhin Oregon, and Adamant Cellars
- Still actively buying — do not drain long-agers aggressively

### Seasonal Preferences

- **Spring/Summer (May–Sep):** Prioritize sparkling, rosé, whites, and lighter reds (Pinot Noir, Bardolino, lighter Italian)
- **Fall/Winter (Oct–Apr):** Prioritize big reds — Washington Cab/Syrah/Merlot, Barolo, Bordeaux, Rhône blends
- **Holiday anchors:** Slot a special bottle at Thanksgiving (late Nov), Christmas/holiday dinner (mid-Dec), New Year's Eve (late Dec), Valentine's Day (mid-Feb), 4th of July (early Jul), Anniversary (May 28)

### Prioritization Order

1. **Past peak** — bottles where current year > `EndConsume`. Open immediately regardless of season. Flag with urgent indicator.
2. **Expiring this year** — bottles where `EndConsume` = current year. Schedule in next 8 weeks.
3. **Expiring next year** — bottles where `EndConsume` = current year + 1. Schedule within current plan horizon.
4. **Peak window** — bottles where `BeginConsume` ≤ current year ≤ `EndConsume`. Schedule seasonally.
5. **Just entering window** — bottles where `BeginConsume` = current year or current year + 1. Schedule toward end of horizon.
6. **Long-agers** — bottles where `BeginConsume` > current year + 2. Hold in cellar; do not schedule unless specifically requested.

### Evolution Tracking

Open one bottle per year from each of these labels to monitor development. Pick the most urgent vintage within the drinking window each year:

- Domaine Drouhin Oregon Pinot Noir **Laurène** — schedule in fall (Oct–Nov), Thanksgiving week preferred
- Domaine Drouhin Oregon Pinot Noir **Louise** — schedule in winter (Dec), holiday dinner preferred
- Drouhin Oregon **Roserock** Pinot Noir — schedule in winter (Feb), Valentine's week preferred

### Long-Ager Hold List

Do not schedule these unless `EndConsume` is within 2 years or explicitly requested:

- DDO Roserock 2022, 2024
- DDO Laurène 2021, 2022, 2023
- DDO Louise 2021, 2022, 2023
- DDO Pinot Noir 2019, 2022, 2024
- Caymus Cabernet Sauvignon 2023
- DDO Arthur Chardonnay 2023, 2024
- Adamant Cab Don't Be a Dull Boy 2021 (hold 2 bottles minimum)
- DDO Origine 36, 37
- Dion Old Vines 2020, 2021

### Past-Peak Handling

- Open all past-peak bottles in the first 6–8 weeks of the plan
- Flag with urgent indicator and a note acknowledging the wine may be declining
- Do not discard from plan — include with honest tasting note expectation

### Output

- Write to `site/plan.json` (not `site/index.html`)
- Include `allWeeks` array (52 entries), `quarterInfo` object, and `changelog` object
- Update the `changelog` with changes made in this sync
- All wine metadata (badge, varietal, appellation, scores, windows) from inventory.json
- Do not write credentials to any file
