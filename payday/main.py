#main.py
"""

CLI entrypoint:
- Reads input text (file path arg or stdin)
- Parses into structured rows
- Writes CSV with total + watermark
- Emits concise log messages and exit codes

Exit codes:
 0 = success
 1 = parsed no rows
 2 = input error (e.g., file missing, no stdin)
"""

import sys
from pathlib import Path

from core.parser import WorkHourParser
from infra.logger import LoggerFactory
from pdio.writer import CsvWriter

log = LoggerFactory.get_logger("payday.main")


def _read_input_text(argv):
    """File path via argv[1] or stdin; error if neither."""
    if len(argv) >= 2:
        p = Path(argv[1])
        if not p.exists():
            raise FileNotFoundError(f"Input file not found: {p}")
        return p.read_text(encoding="utf-8")
    if sys.stdin.isatty():
        raise RuntimeError("No input provided. Pass a file path or pipe text via stdin.")
    return sys.stdin.read()


def main(argv):
    try:
        raw = _read_input_text(argv)
    except Exception as e:
        log.error(str(e))
        return 2

    parser = WorkHourParser()
    rows = parser.parse(raw)

    if not rows:
        log.error("No valid work entries parsed. Nothing to write.")
        return 1

    writer = CsvWriter()  # defaults to CWD / "work hour.csv"
    out_path = writer.write(rows)
    log.info("Wrote %d row(s) -> %s", len(rows), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
