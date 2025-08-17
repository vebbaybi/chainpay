"""
payday\pdio\writer.py
CSV writer for structured work-hour rows.

Responsibilities:
- Ensure output directory exists
- Write structured rows to CSV
- Append weekly total
- Add watermark footer
"""

import csv
from pathlib import Path

from infra.constants import WATERMARK


class CsvWriter:
    """CSV writer with watermark and weekly total support."""

    def __init__(self, out_path=None):
        self.out_path = Path(out_path) if out_path else Path.cwd() / "cpd.csv"

    def write(self, rows):
        """Write parsed rows into a CSV file with totals and watermark."""
        weekly_total = sum(r.get("Hours", 0.0) or 0.0 for r in rows)

        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        with self.out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Day", "TimeBlocks", "Location", "Tasks/Details", "Client(s)", "Hours"])
            for r in rows:
                w.writerow([
                    r.get("Day", "NaN"),
                    r.get("TimeBlocks", "NaN"),
                    r.get("Location", "NaN"),
                    r.get("Tasks/Details", "NaN"),
                    r.get("Client(s)", "NaN"),
                    f"{r.get('Hours', 0.0):.1f}",
                ])
            w.writerow(["TOTAL", "", "", "", "", f"{weekly_total:.1f}"])
            f.write(f"# {WATERMARK}\n")

        return self.out_path
