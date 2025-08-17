#payday\utils\textutils.py

import re
from infra.constants import TITLE_MINOR_WORDS


class TextTools:
    """Stateless text utilities."""

    @staticmethod
    def clean_text(s):
        """Normalize dashes to '-' and collapse whitespace."""
        s = s.replace("\u2013", "-").replace("\u2014", "-").replace("—", "-").replace("–", "-")
        return re.sub(r"[ \t]+", " ", s.strip())

    @staticmethod
    def is_acronym(token):
        """Heuristically detect acronym/initialism tokens to preserve uppercase."""
        t = re.sub(r"[.\-/&]", "", token)
        if len(t) >= 2 and t.isupper():
            return True
        if re.fullmatch(r"[A-Z]\d+|[A-Z]{1}\.[A-Z]{1}\.?|[A-Z]\w*\d+", token):
            return True
        return False

    @classmethod
    def smart_title_case(cls, text):
        """Title-case with acronym and minor-word awareness."""
        if not text or text == "NaN":
            return text

        def transform_segment(seg):
            tokens = re.split(r"(\s+)", seg.strip())
            out, is_first_word = [], True
            for tok in tokens:
                if tok.isspace():
                    out.append(tok)
                    continue
                raw = tok
                base = re.sub(r'^[\"\'(\[]|[\"\'\)\]]$', "", raw)
                if cls.is_acronym(base):
                    out.append(raw)
                else:
                    low = base.lower()
                    if not is_first_word and low in TITLE_MINOR_WORDS:
                        fixed = low
                    else:
                        fixed = low.capitalize()
                    out.append(re.sub(re.escape(base), fixed, raw))
                is_first_word = False if raw.strip() else is_first_word
            return "".join(out)

        parts = re.split(r"([,/])", text)
        for i in range(0, len(parts), 2):
            parts[i] = transform_segment(parts[i])
        return "".join(parts)

    @classmethod
    def smart_sentence_case(cls, text):
        """Sentence-case per semicolon segment; preserve acronyms and spacing."""
        if not text or text == "NaN":
            return text

        segs = [s.strip() for s in re.split(r"\s*;\s*", text) if s.strip()]
        out_segs = []
        for seg in segs:
            if cls.is_acronym(seg):
                out_segs.append(seg)
                continue
            words = re.split(r"(\s+)", seg)
            built, made_cap = [], False
            for w in words:
                if w.isspace():
                    built.append(w)
                    continue
                if cls.is_acronym(w):
                    built.append(w)
                else:
                    if not made_cap:
                        def cap_first_alpha(t):
                            for idx, ch in enumerate(t):
                                if ch.isalpha():
                                    return t[:idx] + ch.upper() + t[idx+1:].lower()
                            return t
                        built.append(cap_first_alpha(w))
                        made_cap = True
                    else:
                        built.append(w.lower())
            out_segs.append("".join(built).strip())
        return "; ".join(out_segs)
