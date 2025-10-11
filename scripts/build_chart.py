#!/usr/bin/env python3
# Generates charts/training.png from data/training.csv
import csv, pathlib, io, re
from collections import Counter, OrderedDict
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "training.csv"
OUT_DIR  = ROOT / "charts"
OUT_DIR.mkdir(exist_ok=True)

# --- robust CSV reader (handles BOM, ; or \t delimiters) ---
def _load_csv_text(p: pathlib.Path) -> str:
    raw = p.read_bytes().decode("utf-8-sig", errors="replace")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    if "\t" in raw and raw.count("\t") > raw.count(",") and raw.count("\t") > raw.count(";"):
        raw = raw.replace("\t", ",")
    if raw.count(";") > raw.count(","):
        raw = raw.replace(";", ",")
    return raw

def read_rows(path: pathlib.Path):
    text = _load_csv_text(path)
    f = io.StringIO(text)
    rdr = csv.reader(f)
    try:
        header = next(rdr)
    except StopIteration:
        return []
    cols = [re.sub(r"\s+", " ", (h or "")).strip().lower() for h in header]
    rows = []
    for row in rdr:
        if not any((c or "").strip() for c in row): continue
        if len(row) < len(cols): row += [""] * (len(cols) - len(row))
        rows.append({cols[i]: (row[i] or "").strip() for i in range(len(cols))})
    return rows

num_re = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
def parse_hours(s: str) -> float:
    if not s: return 0.0
    s = s.replace(",", ".")
    m = num_re.search(s)
    return float(m.group(0)) if m else 0.0

rows = read_rows(CSV_PATH)
if not rows:
    # produce an empty placeholder chart
    fig, ax = plt.subplots(figsize=(9,3), dpi=200)
    ax.text(0.5, 0.5, "No data yet", ha="center", va="center", fontsize=16)
    ax.axis("off")
    fig.savefig(OUT_DIR / "training.png", bbox_inches="tight", transparent=True)
    raise SystemExit(0)

need = {"category","hours"}
if not need.issubset(set(rows[0].keys())):
    raise SystemExit(f"CSV must include headers: {sorted(need)}")

# aggregate
totals = Counter()
for r in rows:
    cat = (r.get("category") or "").strip()
    hrs = parse_hours(r.get("hours", "0"))
    if cat: totals[cat] += hrs

# consistent ordering (groups first, then others)
priority = ["GCP","Azure","AWS","Active Directory","Linux","Public Speaking"]
ordered = OrderedDict()
for p in priority:
    if p in totals: ordered[p] = totals[p]
for k in sorted(totals.keys(), key=str.lower):
    if k not in ordered: ordered[k] = totals[k]

labels = list(ordered.keys())
values = [ordered[k] for k in labels]

# brand colors (fallback to slate)
palette = {
    "GCP": "#4285F4",
    "Azure": "#0078D4",
    "AWS": "#FF9900",
    "Active Directory": "#0067B8",
    "Linux": "#000000",
    "Public Speaking": "#9333EA",
}
colors = [palette.get(k, "#334155") for k in labels]

# --- draw chart ---
plt.rcParams.update({"font.size": 11})
fig, ax = plt.subplots(figsize=(10, 4), dpi=200)
bars = ax.barh(labels, values, color=colors, edgecolor="#0D1117", linewidth=0.5)
ax.invert_yaxis()

# value labels
for b in bars:
    w = b.get_width()
    ax.text(w + max(values)*0.02 if values else 0.2, b.get_y()+b.get_height()/2,
            f"{w:.2f}h", va="center", fontsize=10)

ax.set_xlabel("Hours (total)")
ax.set_ylabel("")
ax.grid(axis="x", linestyle=":", alpha=0.3)
ax.set_axisbelow(True)
for spine in ["top","right","left","bottom"]:
    ax.spines[spine].set_alpha(0.15)

fig.tight_layout()
fig.savefig(OUT_DIR / "training.png", bbox_inches="tight", transparent=True)
