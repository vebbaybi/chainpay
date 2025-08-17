#payday\utils\extractors.py

import re
from infra.constants import DAY_MAPPING, DAY_NAMES
from patterns.patterns import LOC_AT, CLIENT_WITH, CLIENT_FOR, DAY_PATTERN
from utils.textutils import TextTools


class FieldExtractors:
    """Helpers to extract day, location, client, and task from text segments."""

    @staticmethod
    def derive_day(text):
        """Return canonical day name if present in text, else 'Unknown'."""
        m = DAY_PATTERN.search(text)
        if not m:
            return "Unknown"
        token = m.group(0).lower()
        if token in DAY_NAMES:
            return token.capitalize()
        return DAY_MAPPING.get(token, token.capitalize())

    @staticmethod
    def split_loc_task_from_at_chunk(chunk):
        """
        For 'at ...' capture, return (location, trailing_task_if_any).
        - Cut location BEFORE 'for/with'
        - Use comma to separate trailing task if present
        """
        part = TextTools.clean_text(chunk)
        original = part
        part = re.split(r"\b(?:for|with)\b", part, flags=re.IGNORECASE)[0].strip()
        if "," in part:
            loc, rest = part.split(",", 1)
            return TextTools.clean_text(loc), TextTools.clean_text(rest)
        m = re.match(r"^([^,]+),\s*([^,]+)\s*(?=\b(?:for|with)\b)", original, flags=re.IGNORECASE)
        if m:
            return TextTools.clean_text(m.group(1)), TextTools.clean_text(m.group(2))
        return TextTools.clean_text(part), ""

    @staticmethod
    def extract_first(text, pattern):
        """Return first regex capture group or empty string."""
        m = pattern.search(text)
        return TextTools.clean_text(m.group(1)) if m else ""

    @staticmethod
    def strip_directives(text):
        """Remove 'at ...', 'for ...', 'with ...' directives."""
        t = text
        t = re.sub(r"\bat\s+[A-Za-z0-9][\w\-\s&.,'#/]+", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\bfor\s+[A-Za-z0-9][\w&\-\s]+", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\bwith\s+[A-Za-z0-9][\w&\-\s]+", "", t, flags=re.IGNORECASE)
        return TextTools.clean_text(t.strip(" ,-;"))

    @classmethod
    def parse_eq_tail(cls, after_eq):
        """
        Parse segments with '=' into (location, client, task).
        Precedence:
          1) 'at ...' → location (+ trailing task)
          2) 'for/with ...' → client
          3) task = after client comma, else trailing from 'at', else residual
        """
        location, client, task = "NaN", "NaN", "NaN"

        at_chunk = cls.extract_first(after_eq, LOC_AT)
        loc_tail = ""
        if at_chunk:
            loc_val, loc_tail = cls.split_loc_task_from_at_chunk(at_chunk)
            if loc_val:
                location = loc_val

        client_candidate = cls.extract_first(after_eq, CLIENT_FOR) or cls.extract_first(after_eq, CLIENT_WITH)
        if client_candidate:
            client = client_candidate

        m = re.search(r"\b(?:with|for)\b\s+[A-Za-z0-9][\w&\-\s]+,\s*(.+)$", after_eq, flags=re.IGNORECASE)
        if m and TextTools.clean_text(m.group(1)):
            task = TextTools.clean_text(m.group(1))
        elif loc_tail:
            task = loc_tail
        else:
            residual = cls.strip_directives(after_eq)
            if residual:
                task = residual

        return location, client, task
