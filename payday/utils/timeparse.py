#payday\utils\timeparse.py
"""
Time parsing utilities implemented as a class.
- TimeParser.to_dt(token, ref_date)
- TimeParser.extract_time_range(text)
"""

import re
from datetime import date, datetime, timedelta
from dateutil import parser as dateparser

from patterns.patterns import TIME_RANGE_GENERIC


class TimeParser:
    """Time token → datetime parsing and time-range extraction."""

    @staticmethod
    def to_dt(tok, ref_date=None):
        """Convert a time token string into a datetime on ref_date (or today)."""
        tok = tok.strip().lower().replace("a.m.", "am").replace("p.m.", "pm")

        # HHMM (e.g., 0930) with optional am/pm suffix
        m = re.fullmatch(r"(?:[01]\d|2[0-3])[0-5]\d(?:\s*(?:am|pm))?", tok)
        if m:
            hh, mm = int(tok[:2]), int(tok[2:4])
            if tok.endswith("pm") and hh < 12:
                hh += 12
            if tok.endswith("am") and hh == 12:
                hh = 0
            today = date.today() if ref_date is None else ref_date
            return datetime(today.year, today.month, today.day, hh, mm)

        # H am/pm (minutes default to 00)
        m = re.fullmatch(r"([01]?\d|2[0-3])\s*(am|pm)", tok)
        if m:
            hh, ap = int(m.group(1)), m.group(2)
            if ap == "pm" and hh < 12:
                hh += 12
            if ap == "am" and hh == 12:
                hh = 0
            today = date.today() if ref_date is None else ref_date
            return datetime(today.year, today.month, today.day, hh, 0)

        # H:MM with optional am/pm
        m = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)\s*(am|pm)?", tok)
        if m:
            hh, mm, ap = int(m.group(1)), int(m.group(2)), m.group(3)
            if ap == "pm" and hh < 12:
                hh += 12
            if ap == "am" and hh == 12:
                hh = 0
            today = date.today() if ref_date is None else ref_date
            return datetime(today.year, today.month, today.day, hh, mm)

        # Fallback: dateutil parser (fuzzy)
        try:
            dt = dateparser.parse(tok, fuzzy=True)
        except Exception:
            dt = None
        if dt:
            today = date.today() if ref_date is None else ref_date
            return dt.replace(year=today.year, month=today.month, day=today.day)
        return None

    @classmethod
    def extract_time_range(cls, text):
        """
        Extract first start/end time range from text.
        Returns (start_dt, end_dt, "HHMM-HHMM", match_end_index) or None.
        """
        g = TIME_RANGE_GENERIC.search(text)
        if not g:
            return None
        s_tok, e_tok = g.group(1), g.group(2)
        ref = date.today()
        s_dt = cls.to_dt(s_tok, ref)
        e_dt = cls.to_dt(e_tok, ref)
        if not s_dt or not e_dt:
            return None
        if e_dt <= s_dt:
            # overnight span
            e_dt = e_dt + timedelta(days=1)
        span = s_dt.strftime("%H%M") + "-" + e_dt.strftime("%H%M")
        return s_dt, e_dt, span, g.end()
