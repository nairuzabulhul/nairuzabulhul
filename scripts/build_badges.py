#!/usr/bin/env python3
import csv, json, collections, pathlib, sys, datetime
from typing import Dict

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "training.csv"
GOALS_PATH = ROOT / "data" / "goals.yml"
OUT_DIR = ROOT / "badges"

def load_goals() -> Dict[str, float]:
    if not GOALS_PATH.exists():
        return {}
    try:
        import yaml
    except ImportError:
        print("No PyYAML found; goals.yml ignored (install PyYAML to enable).")
        return {}
    with GOALS_PATH.open() as f:
        raw = yaml.safe_load(f) or {}
    return {str(k): float(v) for k, v in raw.items()}

def color_for(value: float, goal: float) -> str:
    if goal <= 0:
        return "blue"
    pct = value / goal
    if pct >= 1.0:
        return "brightgreen"
    if pct >= 0.75:
        return "green"
    if pct >= 0.5:
        return "yellow"
    if pct >= 0.25:
        return "orange"
    return "red"

def shield(label: str, value: float, color: str) -> dict:
    # Shields endpoint schema
    return {
        "schemaVersion": 1,
        "label": f"{label} Hours",
        "message": f"{value:.2f}",
        "color": color
    }

def main():
    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} not found", file=sys.stderr)
        sys.exit(1)

    totals = collections.Counter()
    with CSV_PATH.open(newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            cat = (row.get("category") or "").strip()
            if not cat:
                continue
            try:
                hrs = float(row.get("hours", 0) or 0)
            except ValueError:
                continue
            totals[cat] += hrs

    # Always include a Total
    total_hours = sum(totals.values())
    totals["Total"] = total_hours

    goals = load_goals()
    OUT_DIR.mkdir(exist_ok=True)

    for cat, val in totals.items():
        goal = goals.get(cat, 0.0)
        color = color_for(val, goal)
        payload = shield(cat, val, color)
        (OUT_DIR / f"{cat.lower().replace(' ', '_')}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    # Optional: a compact summary file you can consume elsewhere
    summary = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "totals": dict(totals),
        "goals": goals
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

if __name__ == "__main__":
    main()
