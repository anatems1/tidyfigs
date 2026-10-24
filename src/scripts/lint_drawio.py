#!/usr/bin/env python3
"""
lint_drawio.py — catch structural errors, theme drift, text overflow, overlaps and sloppy spacing.

    python lint_drawio.py fig.drawio --theme theme.yaml [--scale 1.0] [--json report.json]

Checks
  ERROR  invalid XML, duplicate ids, missing parent/source/target, ';base64' in image data URIs
         (breaks draw.io style parsing), missing geometry
  WARN   off-theme colors / font families / font sizes, text overflowing its cell, overlapping
         text, elements outside the page, near-miss alignments (1-3 px), unequal sizes or gaps
         among siblings that look like a row/column
  INFO   counts per element type
Exit status 1 when any ERROR is found.
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drawio_kit import Theme, html_lines, measure_line, measure_math  # noqa: E402
import html as _html
from render_preview import load_model, parse_style, fnum  # noqa: E402

COLOR_KEYS = ("fillColor", "strokeColor", "fontColor", "imageBorder", "labelBackgroundColor", "gradientColor")


def lint(path, theme_path=None, scale=1.0, max_items=25):
    errors, warns, infos = [], [], []
    try:
        model = load_model(path)
    except Exception as e:
        return dict(errors=[f"cannot parse: {e}"], warnings=[], info=[])
    root = model.find("root")
    cells = []
    for o in root:
        c = o if o.tag == "mxCell" else o.find("mxCell")
        if c is None:
            continue
        if o.tag != "mxCell":
            c.set("id", o.get("id")); c.set("value", o.get("label", ""))
        cells.append(c)
    ids = Counter(c.get("id") for c in cells)
    for i, n in ids.items():
        if n > 1:
            errors.append(f"duplicate id '{i}' ({n}x)")
    by_id = {c.get("id"): c for c in cells}
    for c in cells:
        p = c.get("parent")
        if c.get("id") not in ("0",) and p and p not in by_id:
            errors.append(f"{c.get('id')}: parent '{p}' missing")
        for k in ("source", "target"):
            if c.get(k) and c.get(k) not in by_id:
                errors.append(f"{c.get('id')}: {k} '{c.get(k)}' missing")
        st = c.get("style") or ""
        if re.search(r"image=data:image/[\w+.-]+;base64", st):
            errors.append(f"{c.get('id')}: image data URI uses ';base64,' — draw.io needs 'data:image/png,<b64>'")
        if (c.get("vertex") == "1" or c.get("edge") == "1") and c.find("mxGeometry") is None:
            errors.append(f"{c.get('id')}: no mxGeometry")

    # absolute geometry
    absg = {}

    def ag(cid):
        if cid in absg:
            return absg[cid]
        c = by_id[cid]
        g = c.find("mxGeometry")
        if g is None:
            absg[cid] = None; return None
        x, y, w, h = (fnum(g.attrib, k, 0) for k in ("x", "y", "width", "height"))
        p = c.get("parent")
        if p in by_id and by_id[p].get("vertex") == "1":
            pg = ag(p)
            if pg:
                x, y = x + pg[0], y + pg[1]
        absg[cid] = (x, y, w, h)
        return absg[cid]

    verts = [c for c in cells if c.get("vertex") == "1"]
    edges = [c for c in cells if c.get("edge") == "1"]
    pw, ph = fnum(model.attrib, "pageWidth", 0), fnum(model.attrib, "pageHeight", 0)

    # theme
    th = Theme.load(theme_path) if theme_path else None
    off_colors, off_fonts, off_sizes = Counter(), Counter(), Counter()
    if th:
        palette = set(th.colors.values()) | {"none", "default", "#ffffff00"}
        families = {v["family"] for v in th.fonts.values()}
        sizes = {round(float(v) * scale, 2) for v in th.sizes.values()}
    kinds = Counter()
    texts = []
    for c in cells:
        tokens, kv = parse_style(c.get("style"))
        if th:
            for k in COLOR_KEYS:
                v = kv.get(k)
                if v and v.lower() not in palette:
                    off_colors[v.lower()] += 1
            for m in re.finditer(r'color="?(#[0-9a-fA-F]{3,6})', c.get("value") or ""):
                if m.group(1).lower() not in palette:
                    off_colors[m.group(1).lower()] += 1
            if c.get("value") and kv.get("fontFamily") and kv["fontFamily"] not in families:
                off_fonts[kv["fontFamily"]] += 1
            if c.get("value") and "fontSize" in kv and round(float(kv["fontSize"]), 2) not in sizes:
                if not re.fullmatch(r"[\W\s]*", re.sub(r"<[^>]+>", "", c.get("value") or "")):  # ignore icon glyphs
                    off_sizes[kv["fontSize"]] += 1
        if c.get("vertex") != "1":
            continue
        g = ag(c.get("id"))
        if g is None:
            continue
        x, y, w, h = g
        kind = ("group" if "group" in tokens else "text" if "text" in tokens else
                "image" if kv.get("shape") == "image" else kv.get("shape") or next((t for t in tokens if t in ("ellipse", "rhombus", "triangle")), "rect"))
        kinds[kind] += 1
        rot = abs(fnum(kv, "rotation", 0)) % 180
        bx, by, bw, bh = (x + w / 2 - h / 2, y + h / 2 - w / 2, h, w) if 45 < rot < 135 else (x, y, w, h)
        if pw and (bx < -1 or by < -1 or bx + bw > pw + 1 or by + bh > ph + 1):
            warns.append(f"{c.get('id')}: outside page ({x:.0f},{y:.0f},{w:.0f}x{h:.0f}) vs page {pw:.0f}x{ph:.0f}")
        val = c.get("value") or ""
        if val and kind != "group":
            lines = html_lines(val) if kv.get("html") == "1" else html_lines(val, raw_text=True)
            plain = " / ".join("".join(s["text"] for s in l) for l in lines).strip(" /")
            if not plain:
                continue
            fam = kv.get("fontFamily", "Helvetica"); size = fnum(kv, "fontSize", 11)
            mm = re.fullmatch(r"\s*\$\$(.+)\$\$\s*", _html.unescape(plain), re.S)
            if mm:   # LaTeX label: measure the rendered math, not the source
                mw, mh = measure_math(mm.group(1), size)
                al = kv.get("align", "center")
                tx = x if al == "left" else x + w - mw if al == "right" else x + (w - mw) / 2
                if mw > w * 1.05 + 4:
                    warns.append(f"{c.get('id')}: equation is {mw:.0f}px wide but its box is {w:.0f}px")
                texts.append((c.get("id"), plain, (tx, y + (h - mh) / 2, mw, mh)))
                continue
            bold = int(fnum(kv, "fontStyle", 0)) & 1
            if bold:
                for l in lines:
                    for s in l: s["bold"] = True
            spacing = fnum(kv, "spacing", 2)
            avail = w - 2 * spacing - fnum(kv, "spacingLeft", 0) - fnum(kv, "spacingRight", 0)
            widths = [measure_line(l, fam, size) for l in lines]
            nlines = len(lines)
            if kv.get("whiteSpace") == "wrap" and avail > 0:
                nlines = sum(max(1, int(-(-wd // avail))) for wd in widths)
                text_w = min(max(widths), avail)
            else:
                text_w = max(widths)
                if text_w > w * 1.02 + 2 and kind != "text":
                    warns.append(f"{c.get('id')}: label '{plain[:40]}' is {text_w:.0f}px wide but the box is {w:.0f}px")
            text_h = nlines * size * 1.2
            if text_h > h * 1.05 + 2 and kv.get("verticalLabelPosition") != "bottom" and kind != "text":
                warns.append(f"{c.get('id')}: label '{plain[:40]}' needs ~{text_h:.0f}px height, box is {h:.0f}px ({nlines} lines)")
            al = kv.get("align", "center")
            tx = x + spacing if al == "left" else x + w - spacing - text_w if al == "right" else x + (w - text_w) / 2
            ty = y + (h - text_h) / 2
            if "rotation" not in kv:
                texts.append((c.get("id"), plain, (tx, ty, text_w, text_h)))
    # overlapping text
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a, b = texts[i][2], texts[j][2]
            ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
            iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
            small = min(a[2] * a[3], b[2] * b[3]) or 1
            if ix * iy / small > 0.15:
                warns.append(f"text overlap: '{texts[i][1][:25]}' ({texts[i][0]}) and '{texts[j][1][:25]}' ({texts[j][0]})")
    # partial overlaps: shapes that intersect without one containing the other, and text that
    # crosses a shape border (both usually mean a crowded or mis-placed element)
    boxes = []
    for c in verts:
        tokens, kv = parse_style(c.get("style"))
        g = ag(c.get("id"))
        if not g or "group" in tokens or "text" in tokens or kv.get("shape") == "image":
            continue
        if g[2] >= 14 and g[3] >= 14 and kv.get("fillColor", "") != "none" or (g[2] >= 14 and g[3] >= 14 and kv.get("strokeColor") not in (None, "none")):
            boxes.append((c.get("id"), g))

    def inter(a, b):
        return (max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])),
                max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])))

    def inside(a, b, tol=1):
        return a[0] >= b[0] - tol and a[1] >= b[1] - tol and a[0] + a[2] <= b[0] + b[2] + tol and a[1] + a[3] <= b[1] + b[3] + tol
    ov = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (ia, a), (ib, b) = boxes[i], boxes[j]
            ix, iy = inter(a, b)
            small = min(a[2] * a[3], b[2] * b[3]) <= 30 * 30   # badges / markers on corners are intentional
            if ix > 2 and iy > 2 and not small and not inside(a, b) and not inside(b, a):
                ov.append(f"shapes overlap: {ia} and {ib} ({ix:.0f}x{iy:.0f}px)")
    for tid, plain, t in texts:
        for bid, b in boxes:
            ix, iy = inter(t, b)
            if ix > 3 and iy > 3 and not inside(t, b, tol=2) and not inside(b, t):
                ov.append(f"text crosses a shape border: '{plain[:30]}' ({tid}) vs {bid}")
    warns += ov[:max_items]
    # alignment / spacing among sized, non-text shapes
    shapes = []
    for c in verts:
        tokens, kv = parse_style(c.get("style"))
        g = ag(c.get("id"))
        if not g or "group" in tokens or "text" in tokens or kv.get("shape") == "image":
            continue
        if g[2] >= 14 and g[3] >= 14:
            shapes.append((c.get("id"), g))
    near = []
    keys = {"left": (lambda g: g[0], 1), "right": (lambda g: g[0] + g[2], 1), "center-x": (lambda g: g[0] + g[2] / 2, 1),
            "top": (lambda g: g[1], 0), "bottom": (lambda g: g[1] + g[3], 0), "center-y": (lambda g: g[1] + g[3] / 2, 0)}

    def contains(a, b):
        return a[0] <= b[0] and a[1] <= b[1] and a[0] + a[2] >= b[0] + b[2] and a[1] + a[3] >= b[1] + b[3]

    def axis_gap(a, b, vertical):  # gap between boxes along the other axis
        if vertical:
            return max(0, max(a[1], b[1]) - min(a[1] + a[3], b[1] + b[3]))
        return max(0, max(a[0], b[0]) - min(a[0] + a[2], b[0] + b[2]))
    for name, (fn, vertical) in keys.items():
        for i in range(len(shapes)):
            for j in range(i + 1, len(shapes)):
                (ia, a), (ib, b) = shapes[i], shapes[j]
                dv = abs(fn(a) - fn(b))
                ratio = max(a[2], a[3]) / max(1, max(b[2], b[3]))
                if (0.6 < dv <= 3 and 1 / 3 <= ratio <= 3 and not contains(a, b) and not contains(b, a)
                        and axis_gap(a, b, vertical) < 120):
                    near.append(f"near-miss {name}: {ia}={fn(a):.1f} vs {ib}={fn(b):.1f} (snap to one value)")
    warns += near[:max_items]
    # rows: same top & height
    rows = defaultdict(list)
    for i, g in shapes:
        rows[(round(g[1] / 4), round(g[3] / 4))].append((i, g))
    for key, items in rows.items():
        if len(items) < 3:
            continue
        items.sort(key=lambda t: t[1][0])
        ws = [g[2] for _, g in items]
        gaps = [b[1][0] - (a[1][0] + a[1][2]) for a, b in zip(items, items[1:])]
        if max(ws) - min(ws) > 1 and max(ws) - min(ws) <= 0.08 * max(ws):
            warns.append(f"row {[i for i, _ in items]}: widths {['%.0f' % w for w in ws]} differ slightly — make equal")
        if all(g > 0 for g in gaps) and max(gaps) - min(gaps) > 3 and max(gaps) - min(gaps) <= 0.6 * max(gaps):
            warns.append(f"row {[i for i, _ in items]}: uneven gaps {['%.0f' % g for g in gaps]} — distribute evenly")
    if th:
        for v, n in off_colors.most_common(max_items):
            warns.append(f"off-theme color {v} used {n}x")
        for v, n in off_fonts.most_common():
            warns.append(f"off-theme font family '{v}' used {n}x")
        for v, n in off_sizes.most_common(max_items):
            warns.append(f"off-theme font size {v} used {n}x (theme sizes x scale: {sorted(sizes)})")
    infos.append(f"{len(verts)} vertices ({dict(kinds)}), {len(edges)} edges")
    return dict(errors=errors, warnings=warns, info=infos)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("drawio"); ap.add_argument("--theme"); ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--json"); ap.add_argument("--max", type=int, default=25)
    a = ap.parse_args()
    r = lint(a.drawio, a.theme, a.scale, a.max)
    for e in r["errors"]:
        print("ERROR ", e)
    for w in r["warnings"]:
        print("WARN  ", w)
    for i in r["info"]:
        print("INFO  ", i)
    print(f"-- {len(r['errors'])} errors, {len(r['warnings'])} warnings")
    if a.json:
        json.dump(r, open(a.json, "w", encoding="utf-8"), indent=1)
    sys.exit(1 if r["errors"] else 0)


if __name__ == "__main__":
    main()
