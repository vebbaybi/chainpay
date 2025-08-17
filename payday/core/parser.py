"""
core/parser.py

WorkHourParser: the central engine that:
- Cleans raw lines
- Splits into segments
- Extracts time ranges, locations, tasks, clients
- Applies policies (lunch deduction, block dedupe)
- Formats text consistently (title/sentence case)
- Produces structured rows ready for CSV
"""

import re

from patterns.patterns import CLIENT_FOR, CLIENT_WITH, LOC_AT
from policies.policies import Policies
from utils.extractors import FieldExtractors
from utils.textutils import TextTools
from utils.timeparse import TimeParser


class WorkHourParser:
    """Transforms free-text work logs into structured row dictionaries."""

    def __init__(self, policies=None):
        self.policies = policies if policies else Policies()
        

    def parse(self, raw_text):
        """
        Parse multi-line text into structured rows.
        Each row: {"Day","TimeBlocks","Location","Tasks/Details","Client(s)","Hours"}
        """
        rows = []
        for raw_line in re.split(r"[\r\n]+", raw_text):
            line = TextTools.clean_text(raw_line)
            if not line:
                continue

            # Day extraction
            day = FieldExtractors.derive_day(line)

            # Split into logical segments
            segments = [s.strip() for s in line.split("|") if s.strip()]
            lunch_flag, lunch_annotate = self.policies.detect_lunch_flags(segments)

            blocks = []
            last_block_index = -1

            for seg in segments:
                # Try to parse time range
                tr = TimeParser.extract_time_range(seg)
                if tr:
                    s_dt, e_dt, span, end_idx = tr
                    seg_tail = seg[end_idx:].strip()

                    location, client, task = "NaN", "NaN", "NaN"
                    if "=" in seg_tail:
                        after_eq = seg_tail.split("=", 1)[1].strip()
                        location, client, task = FieldExtractors.parse_eq_tail(after_eq)
                    else:
                        at_chunk = FieldExtractors.extract_first(seg_tail, LOC_AT)
                        for_name = FieldExtractors.extract_first(seg_tail, CLIENT_FOR)
                        with_name = FieldExtractors.extract_first(seg_tail, CLIENT_WITH)

                        if at_chunk:
                            loc_val, tail_task = FieldExtractors.split_loc_task_from_at_chunk(at_chunk)
                            if loc_val:
                                location = loc_val
                        client_candidate = for_name or with_name
                        if client_candidate:
                            client = client_candidate

                        # Explicit task after client
                        m_task_after_client = re.search(
                            r"\b(?:with|for)\b\s+[A-Za-z0-9][\w&\-\s]+,\s*(.+)$",
                            seg_tail,
                            flags=re.IGNORECASE,
                        )
                        if m_task_after_client and TextTools.clean_text(m_task_after_client.group(1)):
                            task = TextTools.clean_text(m_task_after_client.group(1))
                        else:
                            if at_chunk:
                                _, tail_task = FieldExtractors.split_loc_task_from_at_chunk(at_chunk)
                                if tail_task:
                                    task = tail_task
                            if task == "NaN":
                                before_directive = re.split(r"\b(?:at|with|for)\b", seg_tail, flags=re.IGNORECASE)[0]
                                before_directive = TextTools.clean_text(before_directive.strip("-: ,"))
                                before_directive = re.sub(r"^\d{3,4}\s*-\s*\d{3,4}\s*", "", before_directive)
                                if before_directive:
                                    task = before_directive

                    dur = round((e_dt - s_dt).total_seconds() / 3600.0, 2)
                    blocks.append({
                        "time": span,
                        "location": location,
                        "task": task,
                        "client": client,
                        "hours": dur,
                        "_s_dt": s_dt,
                        "_e_dt": e_dt,
                    })
                    last_block_index = len(blocks) - 1

                else:
                    # Segment modifies the last block
                    if last_block_index < 0:
                        continue
                    blk = blocks[last_block_index]

                    at_chunk = FieldExtractors.extract_first(seg, LOC_AT)
                    if at_chunk:
                        loc_val, tail_task = FieldExtractors.split_loc_task_from_at_chunk(at_chunk)
                        if blk["location"] == "NaN" and loc_val:
                            blk["location"] = loc_val
                        if blk["task"] == "NaN" and tail_task:
                            blk["task"] = tail_task

                    for_name = FieldExtractors.extract_first(seg, CLIENT_FOR)
                    with_name = FieldExtractors.extract_first(seg, CLIENT_WITH)
                    client_candidate = for_name or with_name
                    if blk["client"] == "NaN" and client_candidate:
                        blk["client"] = client_candidate

                    if blk["task"] == "NaN":
                        m = re.search(
                            r"\b(?:with|for)\b\s+[A-Za-z0-9][\w&\-\s]+,\s*(.+)$",
                            seg,
                            flags=re.IGNORECASE,
                        )
                        if m:
                            blk["task"] = TextTools.clean_text(m.group(1))

            if not blocks:
                continue

            # Drop umbrella block if detailed sub-blocks cover it
            blocks = self.policies.drop_covering_block(blocks)

            # Annotate lunch when explicitly mentioned
            if lunch_flag and lunch_annotate and blocks and blocks[0]["task"] != "NaN":
                if "(lunch)" not in blocks[0]["task"].lower():
                    blocks[0]["task"] = TextTools.clean_text(blocks[0]["task"] + " (lunch)")

            # Format outputs
            timeblocks = ", ".join(b["time"] for b in blocks)
            loc_out = ", ".join(TextTools.smart_title_case(b["location"]) for b in blocks)
            tasks_out = ", ".join(TextTools.smart_sentence_case(b["task"]) for b in blocks)
            clients_out = ", ".join(TextTools.smart_title_case(b["client"]) for b in blocks)

            total_hours = self.policies.sum_hours(blocks)
            if lunch_flag:
                total_hours = round(max(0.0, total_hours - self.policies.lunch_deduction_hours), 2)

            rows.append({
                "Day": day,
                "TimeBlocks": timeblocks if timeblocks else "NaN",
                "Location": loc_out if loc_out.strip() else "NaN",
                "Tasks/Details": tasks_out if tasks_out.strip() else "NaN",
                "Client(s)": clients_out if clients_out.strip() else "NaN",
                "Hours": total_hours,
            })
        return rows
