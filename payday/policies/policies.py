"""
policies/policies.py

Business rules for the payday project.

Encapsulates:
- Lunch deduction logic (default subtract 0.5h)
- Optional lunch annotation on explicit positive mentions
- Covering block de-duplication (tolerance in seconds)
- Stable hour summation
"""

from patterns.patterns import LUNCH_EXPLICIT, LUNCH_NO, LUNCH_POS


class Policies:
    """
    Stateful policy container.

    Parameters (all optional):
      lunch_deduction_hours: hours to subtract when lunch applies (default 0.5)
      annotate_on_positive: append "(lunch)" only when explicitly mentioned (default True)
      subtract_lunch_by_default: if no signals, subtract lunch (default True)
      cover_tolerance_seconds: tolerance for umbrella vs sub-block equality (default 60)
    """

    def __init__(
        self,
        lunch_deduction_hours=0.5,
        annotate_on_positive=True,
        subtract_lunch_by_default=True,
        cover_tolerance_seconds=60,
    ):
        self.lunch_deduction_hours = float(lunch_deduction_hours)
        self.annotate_on_positive = bool(annotate_on_positive)
        self.subtract_lunch_by_default = bool(subtract_lunch_by_default)
        self.cover_tolerance_seconds = int(cover_tolerance_seconds)

    # ----- Lunch policy -----
    def detect_lunch_flags(self, segments):
        """
        Determine lunch policy for a given line.

        Returns (subtract, annotate):
          subtract -> whether to subtract self.lunch_deduction_hours
          annotate -> whether to append "(lunch)" to first task
        Priority:
          1) "lunch: yes/no" explicit directive
          2) Negative cues → no subtract, no annotate
          3) Positive cues → subtract; annotate if enabled
          4) Fallback → self.subtract_lunch_by_default, no annotate
        """
        joined = " | ".join(segments)

        explicit = LUNCH_EXPLICIT.search(joined)
        if explicit:
            v = explicit.group(1).lower()
            if v in ("no", "n"):
                return False, False
            if v in ("yes", "y"):
                return True, bool(self.annotate_on_positive)

        if LUNCH_NO.search(joined):
            return False, False

        if LUNCH_POS.search(joined):
            return True, bool(self.annotate_on_positive)

        return bool(self.subtract_lunch_by_default), False

    # ----- Cover block de-duplication -----
    def drop_covering_block(self, blocks):
        """
        If one block spans [min(start), max(end)] and the remaining ≥2 blocks
        together equal that span within tolerance, drop the umbrella block
        to avoid double-counting.

        Expects each block to include:
          "_s_dt": datetime start
          "_e_dt": datetime end
        """
        if not blocks or len(blocks) < 2:
            return blocks

        starts = [b.get("_s_dt") for b in blocks]
        ends = [b.get("_e_dt") for b in blocks]
        if any(s is None for s in starts) or any(e is None for e in ends):
            return blocks

        min_s = min(starts)
        max_e = max(ends)
        full_span_seconds = (max_e - min_s).total_seconds()

        cover_idxs = [i for i, b in enumerate(blocks) if b.get("_s_dt") == min_s and b.get("_e_dt") == max_e]
        if not cover_idxs:
            return blocks

        tol = abs(int(self.cover_tolerance_seconds))
        for idx in cover_idxs:
            others = [b for j, b in enumerate(blocks) if j != idx]
            if len(others) < 2:
                continue
            others_seconds = sum((b["_e_dt"] - b["_s_dt"]).total_seconds() for b in others)
            if abs(others_seconds - full_span_seconds) <= tol:
                return [b for j, b in enumerate(blocks) if j != idx]

        return blocks

    # ----- Aggregation -----
    def sum_hours(self, blocks):
        """Sum 'hours' across blocks; returns a rounded float (2 decimals)."""
        total = 0.0
        for b in blocks or ():
            total += b.get("hours", 0.0) or 0.0
        return round(total, 2)
