#payday\patterns\patterns.py

import re

from infra.constants import DAY_ABBREVIATIONS, DAY_NAMES

# ---------- Day names / abbreviations ----------
DAY_PATTERN = re.compile(
    r"\b(?:" + "|".join(DAY_NAMES + DAY_ABBREVIATIONS) + r")\b",
    re.IGNORECASE,
)

# ---------- Time tokens and ranges ----------
_TIME_SEP = r"(?:-|–|—|to)"

_TIME_TOKEN_COLON = r"(?:[01]?\d|2[0-3]):[0-5]\d(?:\s*(?:am|pm|a\.m\.|p\.m\.))?"
_TIME_TOKEN_HHMM  = r"(?:[01]\d|2[0-3])[0-5]\d(?:\s*(?:am|pm|a\.m\.|p\.m\.))?"
_TIME_TOKEN_H     = r"(?:[01]?\d|2[0-3])\s*(?:am|pm|a\.m\.|p\.m\.)"

_TIME_ANY = r"(?:%s|%s|%s)" % (
    _TIME_TOKEN_COLON,
    _TIME_TOKEN_HHMM,
    _TIME_TOKEN_H,
)

TIME_RANGE_GENERIC = re.compile(
    r"(?:from\s+)?(" + _TIME_ANY + r")\s*(?:" + _TIME_SEP + r")\s*(?:to\s+)?(" + _TIME_ANY + r")",
    re.IGNORECASE,
)

# ---------- Extractors ----------
LOC_AT      = re.compile(r"\bat\s+([A-Za-z0-9][\w\-\s&.,'#/]+)", re.IGNORECASE)
CLIENT_WITH = re.compile(r"\bwith\s+([A-Za-z0-9][\w&\-\s]+)\b", re.IGNORECASE)
CLIENT_FOR  = re.compile(r"\bfor\s+([A-Za-z0-9][\w&\-\s]+)\b", re.IGNORECASE)

# ---------- Lunch detection ----------
LUNCH_POS = re.compile(
    r"\b(lunch|break|30\s*min|30\s*mins|30\s*minutes)\b",
    re.IGNORECASE,
)
LUNCH_NO = re.compile(
    r"\b(no\s*lunch|skip(?:ped)?\s*lunch|without\s+lunch)\b",
    re.IGNORECASE,
)
LUNCH_EXPLICIT = re.compile(
    r"\blunch\s*[:=]\s*(yes|no|y|n)\b",
    re.IGNORECASE,
)
