#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from dateutil import parser as dateparser  # for odd time tokens

WATERMARK = "Compiled with chainpay.py by webbaby https://github.com/vebbaybi/chainpay/blob/main/chainpay.py"

# ---------- Logging ----------
LOGGER = logging.getLogger("workhour.parser")
if not LOGGER.handlers:
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    LOGGER.addHandler(h)
LOGGER.setLevel(logging.INFO)

# ---------- Patterns ----------
_DAY_NAMES = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
_DAY_ABBR  = ["mon","tue","tues","wed","thu","thur","thurs","fri","sat","sun"]
_DAY_PATTERN = re.compile(r"\b(?:" + "|".join(_DAY_NAMES + _DAY_ABBR) + r")\b", re.IGNORECASE)

_TIME_SEP = r"(?:-|–|—|to)"
_TIME_TOKEN_COLON = r"(?:[01]?\d|2[0-3]):[0-5]\d(?:\s*(?:am|pm|a\.m\.|p\.m\.))?"
_TIME_TOKEN_HHMM  = r"(?:[01]\d|2[0-3])[0-5]\d(?:\s*(?:am|pm|a\.m\.|p\.m\.))?"
_TIME_TOKEN_H     = r"(?:[01]?\d|2[0-3])\s*(?:am|pm|a\.m\.|p\.m\.)"
_TIME_ANY         = r"(?:%s|%s|%s)" % (_TIME_TOKEN_COLON, _TIME_TOKEN_HHMM, _TIME_TOKEN_H)

_TIME_RANGE_GENERIC = re.compile(
    r"(?:from\s+)?(" + _TIME_ANY + r")\s*(?:" + _TIME_SEP + r")\s*(?:to\s+)?(" + _TIME_ANY + r")",
    re.IGNORECASE,
)

# Extractors
_LOC_AT      = re.compile(r"\bat\s+([A-Za-z0-9][\w\-\s&.,'#/]+)", re.IGNORECASE)
_CLIENT_WITH = re.compile(r"\bwith\s+([A-Za-z0-9][\w&\-\s]+)\b", re.IGNORECASE)
_CLIENT_FOR  = re.compile(r"\bfor\s+([A-Za-z0-9][\w&\-\s]+)\b", re.IGNORECASE)

# Lunch detection
_LUNCH_POS = re.compile(r"\b(lunch|break|30\s*min|30mins|30\s*minutes)\b", re.IGNORECASE)
_LUNCH_NO  = re.compile(r"\b(no\s*lunch|skip(?:ped)?\s*lunch|without\s+lunch)\b", re.IGNORECASE)
_LUNCH_EXPLICIT = re.compile(r"\blunch\s*[:=]\s*(yes|no|y|n)\b", re.IGNORECASE)

# ---------- Helpers ----------
def _clean_text(s: str) -> str:
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("—", "-").replace("–", "-")
    return re.sub(r"[ \t]+", " ", s.strip())

def _derive_day(text: str) -> str:
    m = _DAY_PATTERN.search(text)
    if not m:
        return "Unknown"
    token = m.group(0).lower()
    mapping = {
        "mon":"Monday","tue":"Tuesday","tues":"Tuesday","wed":"Wednesday",
        "thu":"Thursday","thur":"Thursday","thurs":"Thursday",
        "fri":"Friday","sat":"Saturday","sun":"Sunday"
    }
    full = {k.capitalize(): k.capitalize() for k in _DAY_NAMES}
    if token in full: return full[token]
    return mapping.get(token, token.capitalize())

def _to_dt(tok: str, ref_date: date = None):
    tok = tok.strip().lower().replace("a.m.", "am").replace("p.m.", "pm")
    m = re.fullmatch(r"(?:[01]\d|2[0-3])[0-5]\d(?:\s*(?:am|pm))?", tok)
    if m:
        hh = int(tok[:2]); mm = int(tok[2:4])
        if tok.endswith("pm") and hh < 12: hh += 12
        if tok.endswith("am") and hh == 12: hh = 0
        today = date.today() if ref_date is None else ref_date
        return datetime(today.year, today.month, today.day, hh, mm)
    m = re.fullmatch(r"([01]?\d|2[0-3])\s*(am|pm)", tok)
    if m:
        hh = int(m.group(1)); ap = m.group(2)
        if ap == "pm" and hh < 12: hh += 12
        if ap == "am" and hh == 12: hh = 0
        today = date.today() if ref_date is None else ref_date
        return datetime(today.year, today.month, today.day, hh, 0)
    m = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)\s*(am|pm)?", tok)
    if m:
        hh = int(m.group(1)); mm = int(m.group(2)); ap = m.group(3)
        if ap == "pm" and hh < 12: hh += 12
        if ap == "am" and hh == 12: hh = 0
        today = date.today() if ref_date is None else ref_date
        return datetime(today.year, today.month, today.day, hh, mm)
    try:
        dt = dateparser.parse(tok, fuzzy=True)
    except Exception:
        dt = None
    if dt:
        today = date.today() if ref_date is None else ref_date
        return dt.replace(year=today.year, month=today.month, day=today.day)
    return None

def _extract_time_range(text: str):
    g = _TIME_RANGE_GENERIC.search(text)
    if not g:
        return None
    s_tok, e_tok = g.group(1), g.group(2)
    ref = date.today()
    s_dt = _to_dt(s_tok, ref)
    e_dt = _to_dt(e_tok, ref)
    if not s_dt or not e_dt:
        return None
    if e_dt <= s_dt:
        e_dt = e_dt + timedelta(days=1)
    span = s_dt.strftime("%H%M") + "-" + e_dt.strftime("%H%M")
    return s_dt, e_dt, span, g.end()

def _detect_lunch(segments) -> bool:
    joined = " | ".join(segments)
    explicit = _LUNCH_EXPLICIT.search(joined)
    if explicit:
        v = explicit.group(1).lower()
        if v in ("yes","y"): return True
        if v in ("no","n"):  return False
    if _LUNCH_NO.search(joined): return False
    if _LUNCH_POS.search(joined): return True
    return False

def _split_loc_task_from_at_chunk(chunk: str):
    """
    For the 'at ...' capture, return (location, trailing_task_if_any).
    - Cut the location BEFORE 'for/with'
    - Then split once on comma to get potential trailing task
    """
    part = _clean_text(chunk)
    part = re.split(r"\b(?:for|with)\b", part, flags=re.IGNORECASE)[0].strip()
    if "," in part:
        loc, rest = part.split(",", 1)
        return _clean_text(loc), _clean_text(rest)
    return _clean_text(part), ""

def _extract_first(text: str, pattern: re.Pattern) -> str:
    m = pattern.search(text)
    return _clean_text(m.group(1)) if m else ""

def _strip_directives(text: str) -> str:
    t = text
    t = re.sub(r"\bat\s+[A-Za-z0-9][\w\-\s&.,'#/]+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bfor\s+[A-Za-z0-9][\w&\-\s]+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bwith\s+[A-Za-z0-9][\w&\-\s]+", "", t, flags=re.IGNORECASE)
    return _clean_text(t.strip(" ,-;"))

def _parse_eq_tail(after_eq: str):
    """
    For segments with '=', parse:
      location from 'at ...' (before 'for/with' or comma),
      client from 'for/with ...',
      task as the tail after the client comma; else leftover or loc-tail.
    """
    location = "NaN"; client = "NaN"; task = "NaN"

    at_chunk = _extract_first(after_eq, _LOC_AT)
    loc_tail = ""
    if at_chunk:
        loc_val, loc_tail = _split_loc_task_from_at_chunk(at_chunk)
        if loc_val:
            location = loc_val

    client_candidate = _extract_first(after_eq, _CLIENT_FOR) or _extract_first(after_eq, _CLIENT_WITH)
    if client_candidate:
        client = client_candidate

    m = re.search(r"\b(?:with|for)\b\s+[A-Za-z0-9][\w&\-\s]+,\s*(.+)$", after_eq, flags=re.IGNORECASE)
    if m:
        task = _clean_text(m.group(1))
    elif loc_tail:
        task = loc_tail
    else:
        residual = _strip_directives(after_eq)
        if residual:
            task = residual

    return location, client, task

def _sum_hours(blocks):
    total = 0.0
    for b in blocks:
        total += b["hours"]
    return round(total, 2)

# ---------- Core ----------
class WorkHourParser:
    def parse(self, raw_text: str):
        rows = []
        for raw_line in re.split(r"[\r\n]+", raw_text):
            line = _clean_text(raw_line)
            if not line:
                continue

            day = _derive_day(line).lower()

            segments = [s.strip() for s in line.split("|") if s.strip()]
            lunch_flag = _detect_lunch(segments)

            blocks = []
            last_block_index = -1  # modifiers apply ONLY to most recent block on same line

            for seg in segments:
                tr = _extract_time_range(seg)
                if tr:
                    s_dt, e_dt, span, end_idx = tr
                    seg_tail = seg[end_idx:].strip()

                    # Defaults are NaN (no assumptions)
                    task = "NaN"
                    location = "NaN"
                    client = "NaN"

                    # '=' applies only if it appears AFTER the time range
                    if "=" in seg_tail:
                        after_eq = seg_tail.split("=", 1)[1].strip()
                        location, client, task = _parse_eq_tail(after_eq)
                    else:
                        # Free text before directives becomes the task
                        at_chunk  = _extract_first(seg_tail, _LOC_AT)
                        for_name  = _extract_first(seg_tail, _CLIENT_FOR)
                        with_name = _extract_first(seg_tail, _CLIENT_WITH)
                        if at_chunk:
                            loc_val, _ = _split_loc_task_from_at_chunk(at_chunk)
                            if loc_val:
                                location = loc_val
                        client_candidate = for_name or with_name
                        if client_candidate:
                            client = client_candidate

                        before_directive = re.split(r"\b(?:at|with|for)\b", seg_tail, flags=re.IGNORECASE)[0]
                        before_directive = _clean_text(before_directive.strip("-: ,"))
                        before_directive = re.sub(r"^\d{3,4}\s*-\s*\d{3,4}\s*", "", before_directive)
                        task = before_directive if before_directive else "NaN"

                    dur = round((e_dt - s_dt).total_seconds() / 3600.0, 2)
                    blocks.append({
                        "time": span,
                        "location": location,
                        "task": task,
                        "client": client,
                        "hours": dur,
                    })
                    last_block_index = len(blocks) - 1

                else:
                    # Modifier: applies ONLY to the most recent block on this line
                    if last_block_index < 0:
                        continue
                    blk = blocks[last_block_index]

                    at_chunk = _extract_first(seg, _LOC_AT)
                    if at_chunk:
                        loc_val, tail_task = _split_loc_task_from_at_chunk(at_chunk)
                        if blk["location"] == "NaN" and loc_val:
                            blk["location"] = loc_val
                        # For 'at X, Y' treat Y as task if still NaN
                        if blk["task"] == "NaN" and tail_task:
                            blk["task"] = tail_task

                    for_name  = _extract_first(seg, _CLIENT_FOR)
                    with_name = _extract_first(seg, _CLIENT_WITH)
                    client_candidate = for_name or with_name
                    if blk["client"] == "NaN" and client_candidate:
                        blk["client"] = client_candidate

                    # If modifier is "... for/with CLIENT, TASKDESC" and task is still NaN → set task
                    if blk["task"] == "NaN":
                        m = re.search(r"\b(?:with|for)\b\s+[A-Za-z0-9][\w&\-\s]+,\s*(.+)$", seg, flags=re.IGNORECASE)
                        if m:
                            blk["task"] = _clean_text(m.group(1)).title()  # "JOB Prepping" -> "Job Prepping"

            if not blocks:
                continue

            # Apply lunch once to first task and deduct 0.5h
            if lunch_flag and blocks[0]["task"] != "NaN":
                if "(lunch)" not in blocks[0]["task"].lower():
                    blocks[0]["task"] = blocks[0]["task"] + "(lunch)"

            timeblocks = ", ".join(b["time"] for b in blocks)
            loc_out    = ", ".join(b["location"] for b in blocks)
            tasks_out  = ", ".join(b["task"] for b in blocks)
            clients_out= ", ".join(b["client"] for b in blocks)

            total_hours = _sum_hours(blocks)
            if lunch_flag:
                total_hours = round(max(0.0, total_hours - 0.5), 2)

            rows.append({
                "Day": day,
                "TimeBlocks": timeblocks if timeblocks else "NaN",
                "Location":   loc_out if loc_out else "NaN",
                "Tasks/Details": tasks_out if tasks_out else "NaN",
                "Client(s)":  clients_out if clients_out else "NaN",
                "Hours": total_hours,
            })
        return rows

# ---------- CSV IO ----------
def write_csv(rows, out_path: Path):
    weekly_total = sum(r.get("Hours", 0.0) or 0.0 for r in rows)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        
        w = csv.writer(f)
        w.writerow(["Day", "TimeBlocks", "Location", "Tasks/Details", "Client(s)", "Hours"])
        for r in rows:
            w.writerow([
                r.get("Day","NaN"),
                r.get("TimeBlocks","NaN"),
                r.get("Location","NaN"),
                r.get("Tasks/Details","NaN"),
                r.get("Client(s)","NaN"),
                f"{r.get('Hours', 0.0):.1f}",
            ])
        # Weekly total row
        w.writerow(["TOTAL", "", "", "", "", f"{weekly_total:.1f}"])
        # Watermark as a CSV comment line
        f.write(f"# {WATERMARK}\n")

def _read_input_text(argv):
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
        LOGGER.error(str(e))
        sys.exit(2)

    parser = WorkHourParser()
    rows = parser.parse(raw)

    if not rows:
        LOGGER.error("No valid work entries parsed. Nothing to write.")
        sys.exit(1)

    out_file = Path.cwd() / "work hour.csv"
    write_csv(rows, out_file)
    LOGGER.info("Wrote %d row(s) -> %s", len(rows), out_file)

if __name__ == "__main__":
    main(sys.argv)
