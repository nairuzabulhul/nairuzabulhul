#!/usr/bin/env python3
import csv, json, pathlib, io, re, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "training.csv"
OUT_DIR = ROOT / "badges"

# ---- Helpers ---------------------------------------------------------------

def slugify(name: str) -> str:
    """
    Safe filename from category: lower, non-alnum -> underscore, collapse underscores.
    'Active Directory' -> 'active_directory'
    'GCP' -> 'gcp'
    """
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unnamed"

def read_rows(path: pathlib.Path):
    """
    Robust CSV reader:
    - tolerates UTF-8 BOM
    - tolerates ';' separated exports
    - case-insensitive headers
    - skips blank lines
    """
    if not path.exists():
        raise FileNotFoundError(f"CSV not found at: {path}")

    raw = path.read_bytes().decode("utf-8-sig", errors="replace")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    if raw.count(";") > raw.count(","):
        raw = raw.replace(";", ",")

    f = io.StringIO(raw)
    reader = csv.reader(f)
    try:
        header = next(reader)
    except StopIteration:
        return []

    cols = [h.strip().lower() for h in header]
    rows = []
    for row in reader:
        if not any((c or "").strip() for c in row):
            continue
        # pad short rows
        if len(row) < len(cols):
            row = row + [""] * (len(cols) - len(row))
        rows.append({cols[i]: (row[i] or "").strip() for i in range(len(cols))})
    return rows

def parse_hours(s: str) -> float:
    if s is None:
        return 0.0
    s = s.strip()
    if not s:
        return 0.0
    # allow "2,5" (comma decimal)
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def shield(label: str, value: float, color: str = "blue") -> dict:
    return {
        "schemaVersion": 1,
        "label": f"{label} Hours",
        "message": f"{value:.2f}",
        "color": color
    }

# Simple color ramp vs. optional goals (omit goals for now)
def color_for(value: float) -> str:
    if value >= 40: return "brightgreen"
    if value >= 20: return "green"
    if value >= 10: return "yellow"
    if value >= 5:  return "orange"
    return "blue"

# ---- Main ------------------------------------------------------------------

def main():
    rows = read_rows(CSV_PATH)
    if not rows:
        raise SystemExit("No data in CSV (empty or header only).")

    # Require at least these two columns (case-insensitive)
    have = set(rows[0].keys())
    need = {"category", "hours"}
    missing = need - have
    if missing:
        raise SystemExit(f"CSV missing required column(s): {sorted(missing)} (have: {sorted(have)})")

    # Aggregate hours per category (dynamic)
    totals = {}
    for r in rows:
        cat = (r.get("category") or "").strip()
        if not cat:
            continue
        hrs = parse_hours(r.get("hours"))
        totals[cat] = totals.get(cat, 0.0) + hrs

    # Output directory
    OUT_DIR.mkdir(exist_ok=True)

    # One file per category
    for cat, val in sorted(totals.items(), key=lambda kv: kv[0].lower()):
        out = OUT_DIR / f"{slugify(cat)}.json"
        payload = shield(cat, val, color_for(val))
        out.write_text(json.dumps(payload), encoding="utf-8")
        print(f"Wrote {out} -> {payload}")

    # Total file
    total_val = sum(totals.values())
    (OUT_DIR / "total.json").write_text(
        json.dumps(shield("Total", total_val, color_for(total_val))), encoding="utf-8"
    )
    print(f"Wrote {OUT_DIR/'total.json'} -> Total={total_val:.2f}")

    # Small summary for debugging
    summary = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "csv_path": str(CSV_PATH),
        "categories": totals,
        "total": total_val
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Summary:", json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
