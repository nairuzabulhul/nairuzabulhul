#!/usr/bin/env python3
import csv, json, collections, pathlib, sys, datetime, io, os

# Allow override via env if needed
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV_PATH = pathlib.Path(os.environ.get("TRAINING_CSV", REPO_ROOT / "data" / "training.csv"))
OUT_DIR = pathlib.Path(os.environ.get("BADGES_DIR", REPO_ROOT / "badges"))
GOALS_PATH = REPO_ROOT / "data" / "goals.yml"  # optional

def read_csv_rows(path: pathlib.Path):
    if not path.exists():
        raise FileNotFoundError(f"CSV not found at: {path}")
    text = path.read_bytes().decode("utf-8-sig", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # tolerate semicolon-delimited exports
    if text.count(";") > text.count(","):
        text = text.replace(";", ",")
    f = io.StringIO(text)
    r = csv.reader(f)
    try:
        header = next(r)
    except StopIteration:
        return []
    cols = [h.strip().lower() for h in header]
    rows = []
    for row in r:
        if not any(cell.strip() for cell in row):
            continue
        if len(row) < len(cols):
            row += [""] * (len(cols) - len(row))
        rows.append({cols[i]: row[i].strip() for i in range(len(cols))})
    return rows

def load_goals():
    if not GOALS_PATH.exists():
        return {}
    try:
        import yaml
    except Exception:
        return {}
    data = (GOALS_PATH.read_text(encoding="utf-8") or "").strip()
    if not data:
        return {}
    raw = yaml.safe_load(data) or {}
    goals = {}
    for k, v in raw.items():
        try:
            goals[str(k)] = float(v)
        except Exception:
            pass
    return goals

def color_for(value: float, goal: float) -> str:
    if goal <= 0:
        return "blue"
    pct = value / goal
    if pct >= 1.0: return "brightgreen"
    if pct >= 0.75: return "green"
    if pct >= 0.5: return "yellow"
    if pct >= 0.25: return "orange"
    return "red"

def shield(label: str, value: float, color: str) -> dict:
    return {"schemaVersion": 1, "label": f"{label} Hours", "message": f"{value:.2f}", "color": color}

def main():
    rows = read_csv_rows(CSV_PATH)
    if not rows:
        print("ERROR: CSV is empty or only header.", file=sys.stderr)
        sys.exit(4)

    need = {"category", "hours"}
    have = set(rows[0].keys())
    if not need.issubset(have):
        print(f"ERROR: CSV missing required column(s): {sorted(need - have)}; have={sorted(have)}", file=sys.stderr)
        sys.exit(3)

    totals = collections.Counter()
    skipped = 0
    for r in rows:
        cat = (r.get("category") or "").strip()
        if not cat:
            skipped += 1; continue
        try:
            hrs = float((r.get("hours") or "0").replace(",", "."))
        except Exception:
            skipped += 1; continue
        totals[cat] += hrs

    totals["Total"] = sum(totals.values())
    if sum(totals.values()) == 0:
        print("WARNING: Computed total is 0. Did the CSV contain non-numeric hours?", file=sys.stderr)

    print("== Parsed category totals from CSV ==")
    for k, v in totals.items():
        print(f"{k}: {v:.2f}")

    goals = load_goals()
    OUT_DIR.mkdir(exist_ok=True)

    # Always overwrite JSON from CSV
    for cat, val in totals.items():
        color = color_for(val, goals.get(cat, 0.0))
        payload = shield(cat, val, color)
        out = OUT_DIR / f"{cat.lower().replace(' ', '_')}.json"
        out.write_text(json.dumps(payload), encoding="utf-8")
        print(f"Wrote {out} -> {payload}")

    summary = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "csv_path": str(CSV_PATH),
        "rows_parsed": len(rows),
        "rows_skipped": skipped,
        "categories": dict(totals)
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Summary:", json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
