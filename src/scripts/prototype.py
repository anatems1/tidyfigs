#!/usr/bin/env python3
"""
prototype.py — build all three prototypes of a passage and check them.

    python prototype.py PASSAGE_DIR [--only v2] [--note "what changed"]

Steps: import PASSAGE_DIR/build.py -> for each VARIANTS entry create a Diagram of its canvas size,
call its builder, save  <key>_<name>.drawio  and a preview  <key>_<name>.png  -> lint (theme,
text fit, overlaps, alignment) -> faithfulness check (label words not found in passage.md) ->
prototypes.png contact sheet + prototypes.md summary -> snapshot in _work/iter_NN/ + history.json.

Exit status 1 if a builder raised or any lint ERROR occurred.
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import html
import importlib.util
import json
import os
import re
import shutil
import sys
import traceback
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True   # keep passage folders free of __pycache__
SKILL = os.path.dirname(HERE)

FUNCTION_WORDS = set("""a an the and or of to in on for with by from as at is are be via per vs not no all each
its it this that these those than then into over under between within across e.g i.e etc""".split())


def load_cfg(pdir):
    p = os.path.join(pdir, "_work", "config.json")
    if os.path.exists(p):
        return json.load(open(p))
    theme = next((t for t in (os.path.join(pdir, "theme.yaml"), os.path.join(os.path.dirname(pdir), "theme.yaml"),
                              os.path.join(SKILL, "assets", "theme.yaml")) if os.path.exists(t)), None)
    return dict(scripts=HERE, theme=theme, passage=os.path.join(pdir, "passage.md"), passage_dir=pdir, preview_scale=1.5)


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
        out.append((c.get("id"), latex_words(m.group(1)) if m else plain, plain))
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


def contact_sheet(items, title, out_path):
    from PIL import Image, ImageDraw, ImageFont
    sys.path.insert(0, HERE)
    from drawio_kit import find_font_file
    B = ImageFont.truetype(find_font_file("Helvetica", bold=True), 30)
    R = ImageFont.truetype(find_font_file("Helvetica"), 22)
    W = 1500
    tiles = []
    for png, lab, about in items:
        im = Image.open(png).convert("RGB")
        im = im.resize((W - 60, int(im.height * (W - 60) / im.width)), Image.LANCZOS)
        tiles.append((im, lab, about))
    H = 90 + sum(t[0].height + 110 for t in tiles)
    sheet = Image.new("RGB", (W, H), "#eef1f5")
    dr = ImageDraw.Draw(sheet)
    dr.text((30, 28), title, font=B, fill="#19355d")
    y = 90
    for im, lab, about in tiles:
        dr.text((30, y), lab, font=B, fill="#19355d")
        dr.text((30, y + 40), about[:150], font=R, fill="#333333")
        y += 80
        sheet.paste(im, (30, y)); dr.rectangle([30, y, 30 + im.width, y + im.height], outline="#a4a4a4", width=2)
        y += im.height + 30
    sheet.save(out_path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("passage_dir"); ap.add_argument("--only", help="comma list of variant keys, e.g. v2")
    ap.add_argument("--note", default=""); ap.add_argument("--no-sheet", action="store_true")
    a = ap.parse_args()
    pdir = os.path.abspath(a.passage_dir)
    cfg = load_cfg(pdir)
    sys.path.insert(0, cfg.get("scripts", HERE))
    from drawio_kit import Diagram, Theme
    from lint_drawio import lint
    from render_preview import render_kit

    spec = importlib.util.spec_from_file_location("build_" + str(abs(hash(pdir))), os.path.join(pdir, "build.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    variants = mod.VARIANTS
    if a.only:
        keep = set(a.only.split(","))
        variants = [v for v in variants if v["key"] in keep]
    theme = Theme.load(cfg["theme"])
    passage = open(cfg["passage"]).read() if os.path.exists(cfg["passage"]) else ""
    allowed = getattr(mod, "ALLOWED_TERMS", [])
    inferred = getattr(mod, "INFERRED", [])
    ignore = getattr(mod, "LINT_IGNORE", [])     # substrings of warnings deliberately accepted

    work = os.path.join(pdir, "_work")
    hist_p = os.path.join(work, "history.json")
    hist = json.load(open(hist_p)) if os.path.exists(hist_p) else []
    it = len(hist) + 1
    snap = os.path.join(work, f"iter_{it:02d}")
    os.makedirs(snap, exist_ok=True)

    results, failed = [], False
    for v in variants:
        base = f"{v['key']}_{v['name']}"
        out = os.path.join(pdir, base + ".drawio")
        png = os.path.join(pdir, base + ".png")
        try:
            d = Diagram(*v["size"], theme=theme, scale=v.get("scale", 1.0))
            v["build"](d)
            d.save(out, quiet=True)
        except Exception:
            failed = True
            print(f"[{v['key']}] BUILD FAILED\n" + traceback.format_exc())
            continue
        render_kit(out, png, scale=cfg.get("preview_scale", 1.5))
        L = lint(out, cfg["theme"], v.get("scale", 1.0))
        kept = [w for w in L["warnings"] if not any(k in w for k in ignore)]
        L["ignored"] = len(L["warnings"]) - len(kept)
        L["warnings"] = kept
        miss = faithfulness(out, passage, allowed)
        shutil.copy(out, snap)
        results.append(dict(v=v, out=out, png=png, lint=L, missing=miss, off_theme=sorted(theme.off_theme)))
        theme.off_theme.clear()
        failed |= bool(L["errors"])

    for r in results:
        v = r["v"]
        print(f"\n[{v['key']}] {v['name']}  ->  {os.path.relpath(r['png'], os.getcwd())}")
        for e in r["lint"]["errors"]:
            print("  ERROR", e)
        for w in r["lint"]["warnings"][:12]:
            print("  WARN ", w)
        if r["lint"].get("ignored"):
            print(f"  ({r['lint']['ignored']} warning(s) matched LINT_IGNORE)")
        if len(r["lint"]["warnings"]) > 12:
            print(f"  ... {len(r['lint']['warnings']) - 12} more warnings")
        if r["missing"]:
            print("  NOT IN PASSAGE:", ", ".join(f"{w} ({', '.join(sorted(ids))[:40]})" for w, ids in sorted(r["missing"].items())))
            print("    -> reword with the passage's terms, add to ALLOWED_TERMS (structural words), or list in INFERRED")
    if inferred:
        print("\nINFERRED (report to the user):")
        for x in inferred:
            print("  -", x)

    if results and not a.no_sheet and not a.only:
        title = os.path.basename(pdir)
        m = re.search(r"^#\s+(.+)$", passage, re.M)
        if m:
            title = m.group(1)
        contact_sheet([(r["png"], f"{r['v']['key']} · {r['v']['name'].replace('_', ' ')}", r["v"].get("about", ""))
                       for r in results], f"Prototypes — {title}", os.path.join(pdir, "prototypes.png"))
        md = [f"# Prototypes — {title}", "", "![prototypes](prototypes.png)", ""]
        for r in results:
            v = r["v"]
            md += [f"## {v['key']} · {v['name'].replace('_', ' ')}", "", f"- file: `{os.path.basename(r['out'])}`",
                   f"- about: {v.get('about', '')}", f"- draft caption: {v.get('caption', '') or '—'}",
                   f"- lint: {len(r['lint']['errors'])} errors, {len(r['lint']['warnings'])} warnings",
                   f"- words not in passage: {', '.join(sorted(r['missing'])) or 'none'}", ""]
        md += ["## Inferred content", ""] + [f"- {x}" for x in inferred or ["none"]]
        open(os.path.join(pdir, "prototypes.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
        print(f"\nVIEW: {os.path.join(pdir, 'prototypes.png')}")

    hist.append(dict(iter=it, note=a.note, variants={r["v"]["key"]: dict(errors=len(r["lint"]["errors"]),
                     warnings=len(r["lint"]["warnings"]), not_in_passage=len(r["missing"])) for r in results}))
    json.dump(hist, open(hist_p, "w", encoding="utf-8"), indent=1)
    print("\niter  " + "  ".join(f"{k}(err/warn/miss)" for k in sorted(hist[-1]["variants"])) + "  note")
    for h in hist[-6:]:
        print(f"{h['iter']:>4}  " + "  ".join(f"{v['errors']}/{v['warnings']}/{v['not_in_passage']:<9}" for _, v in sorted(h["variants"].items()))
              + f"  {h['note']}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
