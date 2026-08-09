"""Extract only the consulting-relevant slice of a LinkedIn connections export.

The full export is thousands of private individuals and does not belong in a
repo. This pulls the narrow subset that makes the brief's networking prompt
concrete - people at target firms - and writes first name + last initial only.

Usage:
    python tools/build_network.py "path/to/ConnectionsLinkedin.csv"
"""

from __future__ import annotations

import csv
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "config" / "network.json"

# Firms worth a networking prompt. Order matters only for reporting.
FIRMS = {
    "BCG": r"\bBCG\b|Boston Consulting",
    "Bain": r"\bBain\b",
    "McKinsey": r"McKinsey",
    "Cornerstone Research": r"Cornerstone Research",
    "Analysis Group": r"Analysis Group",
    "Bates White": r"Bates White",
    "Oliver Wyman": r"Oliver Wyman",
    "L.E.K.": r"\bL\.?E\.?K\.?\b",
    "Deloitte": r"Deloitte",
    "EY-Parthenon": r"Parthenon|\bEY\b",
    "Kearney": r"Kearney",
    "Simon-Kucher": r"Simon.?Kucher",
    "Accenture": r"Accenture",
    "Charles River Associates": r"Charles River Associates|\bCRA\b",
}

# Titles that suggest someone who can actually speak to recruiting.
RELEVANT_TITLE = re.compile(
    r"consultant|associate|analyst|partner|manager|principal|recruit|"
    r"engagement|summer|intern|director",
    re.I,
)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    source = pathlib.Path(sys.argv[1])
    rows: list[dict] = []

    with source.open(encoding="utf-8-sig", newline="") as handle:
        # LinkedIn prepends a few notes lines before the real header.
        lines = handle.readlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("First Name,"))

    reader = csv.DictReader(lines[start:])
    total = 0
    for row in reader:
        total += 1
        company = (row.get("Company") or "").strip()
        position = (row.get("Position") or "").strip()
        if not company:
            continue
        for firm, pattern in FIRMS.items():
            if not re.search(pattern, company, re.I):
                continue
            if not RELEVANT_TITLE.search(position):
                continue
            first = (row.get("First Name") or "").strip()
            last = (row.get("Last Name") or "").strip()
            rows.append({
                "name": f"{first} {last[:1]}." if last else first,
                "firm": firm,
                "title": position,
                "connected": (row.get("Connected On") or "").strip(),
            })
            break

    rows.sort(key=lambda r: (r["firm"], r["name"]))
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"Scanned {total} connections -> kept {len(rows)}")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["firm"]] = counts.get(row["firm"], 0) + 1
    for firm, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>4}  {firm}")
    print(f"\nWrote {OUT}")
    print("No emails, no URLs, no full surnames. Private repo only - never public.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
