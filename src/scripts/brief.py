#!/usr/bin/env python3
"""
brief.py — record interview answers and derive the concrete targets.

    python brief.py WORK --set target.venue=elsevier --set target.column=one_and_half \
                         --set target.print_mode=grayscale_safe --set style.font="Times New Roman" \
                         --set style.palette=okabe_ito --set intent.takeaway="..."  --resolve
    python brief.py WORK --show

--resolve derives: target.width_in / min_font_pt from assets/venues.yaml (unless set explicitly),
target.grayscale from print_mode, and applies style.palette (okabe_ito | grayscale | navy_default |
keep | a path to a theme file) and style.font (family name | keep) to WORK/theme.yaml, keeping the
theme's other roles, sizes and strokes. Values are parsed as YAML (numbers, booleans, lists).
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
COLUMN_ALIASES = {"single column": "single", "single": "single", "1.5 column": "one_and_half", "1.5": "one_and_half",
                  "one_and_half": "one_and_half", "double": "double", "full text width (double column)": "double",
                  "full": "double", "double column": "double"}
VENUE_ALIASES = {"ieee journal / conference": "ieee", "elsevier journal": "elsevier", "springer (lncs)": "springer_lncs",
                 "thesis / dissertation": "thesis", "lncs": "springer_lncs", "springer": "springer_lncs"}
PALETTES = {"okabe_ito": "okabe_ito.yaml", "color-blind-safe preset (okabe-ito)": "okabe_ito.yaml",
            "grayscale": "grayscale.yaml", "grayscale preset": "grayscale.yaml", "navy_default": "navy_default.yaml"}


def parse_value(v):
    """'a | b' -> list of strings; true/false/numbers -> typed; everything else stays a raw string."""
    v = v.strip()
    if not v:
        return ""
    if " | " in v:
        return [x.strip() for x in v.split(" | ") if x.strip()]
    try:
        x = yaml.safe_load(v)
        return x if isinstance(x, (bool, int, float)) else v
    except yaml.YAMLError:
        return v


def set_key(d, dotted, value):
    ks = dotted.split(".")
    for k in ks[:-1]:
        d = d.setdefault(k, {}) if isinstance(d.get(k), dict) else d.setdefault(k, {}) if k not in d else d[k]
    d[ks[-1]] = value


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work"); ap.add_argument("--set", action="append", default=[]); ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    bp = os.path.join(a.work, "brief.yaml")
    b = yaml.safe_load(open(bp, encoding="utf-8")) or {}
    explicit = set()
    for kv in a.set:
        k, v = kv.split("=", 1)
        set_key(b, k.strip(), parse_value(v))
        explicit.add(k.strip())
    if a.resolve:
        venues = yaml.safe_load(open(os.path.join(SKILL, "assets", "venues.yaml"), encoding="utf-8"))
        t = b.setdefault("target", {})
        venue = VENUE_ALIASES.get(str(t.get("venue", "generic")).lower(), str(t.get("venue", "generic")).lower())
        col = COLUMN_ALIASES.get(str(t.get("column", "double")).lower(), str(t.get("column", "double")).lower())
        preset = venues.get(venue, venues["generic"])
        cols = preset["columns"]
        if "target.width_in" not in explicit and col in cols:
            t["width_in"] = cols[col]
        elif "target.width_in" not in explicit and col not in cols:
            t["width_in"] = cols.get("double", 7.0)
        if "target.min_font_pt" not in explicit:
            t["min_font_pt"] = preset["min_font_pt"]
        t["venue"], t["column"] = venue, col
        pm = str(t.get("print_mode", "color")).lower()
        t["grayscale"] = "gray" in pm
        if isinstance(t.get("colorblind"), str):
            t["colorblind"] = t["colorblind"].lower().startswith("y")
        # theme edits
        tp = b.get("style", {}).get("theme") or os.path.join(a.work, "theme.yaml")
        theme = yaml.safe_load(open(tp, encoding="utf-8"))
        pal = str(b.get("style", {}).get("palette", "keep"))
        src = PALETTES.get(pal.lower()) if pal.lower() in PALETTES else (pal if os.path.exists(pal) else None)
        if src:
            p = src if os.path.exists(src) else os.path.join(SKILL, "assets", "themes", src)
            new = yaml.safe_load(open(p, encoding="utf-8"))["colors"]
            theme.setdefault("colors", {}).update(new)
            print(f"palette: applied {os.path.basename(p)} to {tp}")
        font = str(b.get("style", {}).get("font", "keep"))
        if font.lower() not in ("keep", "keep current", ""):
            fam = {"times new roman (times-based journals)": "Times New Roman", "helvetica / arial (sans)": "Helvetica",
                   "latin modern / computer modern (latex look)": "Latin Modern Roman"}.get(font.lower(), font)
            theme.setdefault("fonts", {})["paper"] = {"family": fam}
            theme["default_font"] = "paper"
            print(f"font: default label font -> {fam}")
        yaml.safe_dump(theme, open(tp, "w", encoding="utf-8"), sort_keys=False, allow_unicode=True)
    yaml.safe_dump(b, open(bp, "w", encoding="utf-8"), sort_keys=False, allow_unicode=True)
    if a.show or a.resolve:
        t = b.get("target", {})
        print(f"target: {t.get('venue')} {t.get('column')} -> {t.get('width_in')} in, min {t.get('min_font_pt')} pt, "
              f"grayscale {t.get('grayscale')}, colorblind {t.get('colorblind')}")
        print(f"intent: {b.get('intent')}")
        print(f"content: {b.get('content')}")


if __name__ == "__main__":
    main()
