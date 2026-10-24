"""faithful — label words that do not occur in the source text (shared with text-to-drawio).

    from faithful import faithfulness
    missing = faithfulness("fig.drawio", open("passage.md", encoding="utf-8").read(), allowed=["layer"])
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import html
import re
import xml.etree.ElementTree as ET

FUNCTION_WORDS = set("""a an the and or of to in on for with by from as at is are be via per vs not no all each
its it this that these those than then into over under between within across e.g i.e etc""".split())


def tokens(s):
    s = s.replace("\u2011", "-").replace("\u2013", "-")
    out = []
    for t in re.findall(r"[A-Za-z][A-Za-z'\-]*|\d[\d,]*(?:\.\d+)?", s):
        for part in t.split("-"):
            part = part.strip("'").lower().replace(",", "") if part[:1].isdigit() else part.strip("'").lower()
            if part:
                out.append(part)
    return out


def latex_words(latex):
    inner = " ".join(re.findall(r"\\(?:mathrm|text|operatorname|mathit|textbf|mathbf)\{([^}]*)\}", latex))
    rest = re.sub(r"\\[A-Za-z]+", " ", latex)
    return inner + " " + rest


def label_texts(drawio_path):
    root = ET.parse(drawio_path).getroot()
    out = []
    for c in root.iter("mxCell"):
        v = c.get("value") or ""
        if not v:
            continue
        plain = html.unescape(re.sub(r"<br\s*/?>", "\n", v))
        plain = re.sub(r"<[^>]+>", "", plain)
        m = re.fullmatch(r"\s*\$\$(.+)\$\$\s*", plain, re.S)
        text = latex_words(m.group(1)) if m else re.sub(r"\\\((.+?)\\\)", lambda mm: latex_words(mm.group(1)), plain)
        out.append((c.get("id"), text, plain))
    return out


def stem(w):
    for suf, rep in (("ations", ""), ("ation", ""), ("ings", ""), ("ing", ""), ("ions", ""), ("ion", ""),
                     ("ies", "y"), ("ied", "y"), ("es", ""), ("ed", ""), ("s", ""), ("ly", ""), ("al", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: len(w) - len(suf)] + rep
    return w


def faithfulness(drawio_path, passage_text, allowed):
    """Label words that do not occur in the passage (light stemming; acronyms match their expansion)."""
    raw = passage_text + " " + latex_words(passage_text)
    src_list = tokens(raw)
    src = set(src_list)
    stems = {stem(t) for t in src}
    initials = "".join(t[0] for t in src_list if t[0].isalpha())
    allowed = {a.lower() for a in allowed} | FUNCTION_WORDS

    def ok(w):
        if w in src or w in allowed or len(w) <= 2:
            return True
        if w[0].isdigit():
            return w in src
        if stem(w) in stems:
            return True
        if w.isalpha() and 2 <= len(w) <= 6 and w in initials:     # acronym, e.g. llm <- large language model
            return True
        k = min(len(w), 6)
        return any(t[:k] == w[:k] for t in src if len(t) >= k)
    missing = {}
    for cid, text, plain in label_texts(drawio_path):
        for w in tokens(text):
            if not ok(w):
                missing.setdefault(w, set()).add(cid)
    return missing


