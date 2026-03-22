#!/usr/bin/env python3
"""Generate tasting notes for plan entries using Claude Code CLI.

Reads plan.json, identifies entries with empty notes, and calls the
Claude CLI to generate contextual tasting notes for each bottle.

Requires CLAUDE_CODE_OAUTH_TOKEN in the environment.

Usage: generate_notes.py <plan.json>
"""

import json
import subprocess
import sys
from pathlib import Path

BATCH_SIZE = 20  # bottles per Claude call to stay within context


def build_prompt(entries: list[dict]) -> str:
    """Build a prompt for Claude to generate notes."""
    lines = []
    for e in entries:
        urgent = "URGENT — past peak or expiring" if e.get("urgent") else ""
        evolution = "EVOLUTION tasting" if e.get("evolution") else ""
        occasion = f"Occasion: {e['occasion']}" if e.get("occasion") else ""
        flags = " | ".join(filter(None, [urgent, evolution, occasion]))
        lines.append(
            f"Week {e['week']}: {e['vintage']} {e['name']} "
            f"({e.get('appellation', '')}) "
            f"Window: {e.get('window', 'unknown')} Score: {e.get('score', 'none')} "
            f"Badge: {e.get('badge', '')} {flags}"
        )

    bottle_list = "\n".join(lines)
    return f"""Generate a one-sentence tasting note for each wine below. The note should:
- Be 1-2 sentences max, conversational tone
- For urgent/past-peak wines: acknowledge the wine may be declining, suggest decanting or having a backup
- For evolution wines: mention comparing with previous/future vintages
- For holiday occasions: reference the occasion
- For wines in peak window: note what to expect (flavor profile, food pairing suggestion)
- Do NOT invent scores or facts — only reference what's provided

Return ONLY a JSON object mapping week numbers to notes, like:
{{"1": "note text", "2": "note text"}}

Wines:
{bottle_list}"""


def call_claude(prompt: str) -> str:
    """Call Claude CLI with a prompt and return the response."""
    result = subprocess.run(
        ["claude", "--print", "--model", "haiku", prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(
            f"WARNING: Claude CLI returned {result.returncode}: {result.stderr}",
            file=sys.stderr,
        )
        return ""
    return result.stdout.strip()


def extract_json(text: str) -> dict:
    """Extract JSON object from Claude's response."""
    # Find the JSON block
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return {}
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        print("WARNING: Could not parse Claude response as JSON", file=sys.stderr)
        return {}


def generate_notes(plan_path: str) -> None:
    """Generate notes for plan entries with empty notes."""
    plan_data = json.loads(Path(plan_path).read_text())
    all_weeks = plan_data.get("allWeeks", [])

    # Find entries that need notes
    needs_notes = [w for w in all_weeks if not w.get("note")]
    if not needs_notes:
        print("All entries already have notes.")
        return

    print(f"Generating notes for {len(needs_notes)} entries...")

    # Process in batches
    notes_generated = 0
    for i in range(0, len(needs_notes), BATCH_SIZE):
        batch = needs_notes[i : i + BATCH_SIZE]
        prompt = build_prompt(batch)

        print(f"  Batch {i // BATCH_SIZE + 1}: {len(batch)} wines...")
        response = call_claude(prompt)
        if not response:
            print("  WARNING: Empty response for batch, skipping")
            continue

        notes = extract_json(response)
        for week_str, note in notes.items():
            week_num = int(week_str)
            for w in all_weeks:
                if w["week"] == week_num:
                    w["note"] = note
                    notes_generated += 1
                    break

    Path(plan_path).write_text(
        json.dumps(plan_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Generated {notes_generated} notes.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_notes.py <plan.json>", file=sys.stderr)
        sys.exit(1)
    generate_notes(sys.argv[1])
