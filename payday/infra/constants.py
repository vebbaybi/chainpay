#payday\infra\constants.py

"""
infra/constants.py

Immutable project-wide constants in a frozen dataclass.
Provides a singleton `CONSTANTS` plus module-level re-exports.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Constants:
    """Immutable container for shared constants (no imports, no side effects)."""
    watermark = "Compiled with PayDay 1.0"

    # Canonical weekday names and abbreviations
    day_names = [
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday",
    ]
    day_abbreviations = [
        "mon", "tue", "tues", "wed", "thu",
        "thur", "thurs", "fri", "sat", "sun",
    ]
    day_mapping = {
        "mon": "Monday",
        "tue": "Tuesday", "tues": "Tuesday",
        "wed": "Wednesday",
        "thu": "Thursday", "thur": "Thursday", "thurs": "Thursday",
        "fri": "Friday",
        "sat": "Saturday",
        "sun": "Sunday",
    }

    # Minor words to keep lowercase when title-casing
    title_minor_words = {
        "and", "or", "of", "the", "a", "an",
        "at", "by", "for", "from", "in", "on",
        "to", "with", "vs", "via",
    }

    # Default output CSV filename (preserved behavior)
    default_output_filename = "cpd.csv"


# Singleton instance
CONSTANTS = Constants()

# Convenience re-exports
WATERMARK = CONSTANTS.watermark
DAY_NAMES = CONSTANTS.day_names
DAY_ABBREVIATIONS = CONSTANTS.day_abbreviations
DAY_MAPPING = CONSTANTS.day_mapping
TITLE_MINOR_WORDS = CONSTANTS.title_minor_words
DEFAULT_OUTPUT_FILENAME = CONSTANTS.default_output_filename
