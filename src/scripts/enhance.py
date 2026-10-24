#!/usr/bin/env python3
"""
enhance.py — deterministic clean-up passes on ANY .drawio (run after structural edits).

    python enhance.py fig.drawio [-o "fig#ENHANCED.drawio"] --theme theme.yaml --brief brief.yaml \
        --colors --fonts --sizes --strokes --align --attach --fit-page 16 --math [--map "#d6d6d6=neutral"]

Passes (each logs what it changed to stdout and, with --log, appends to a CHANGES.md):
  --colors        snap near-identical colors (CIELAB dE <= --max-de, default 10) to theme colors,
                  express tints as theme role + fillOpacity, keep distinct colors (never erased);
                  --map "#hex=role" or "#hex=role@25" (fill at 25 % opacity) forces a mapping — use it to
                  consolidate a palette deliberately; --add-roles writes kept colors into the theme
  --fonts         set every non-math label to the theme's default font family (or --family NAME)
  --sizes         merge near-identical font sizes into consistent levels (--to-theme: snap levels to
                  theme roles), then raise anything below the brief's minimum print size
  --strokes       snap stroke widths to theme stroke roles; unify arrow-head sizes (--head 6)
  --align         snap near-miss alignments (<= --tol px, default 3) among comparable shapes
  --attach        attach free edge ends lying within --attach-tol px (default 8) of a shape border
  --fit-page M    move content to (M, M) and set the page to content + 2M
  --math          turn the diagram math flag on if any label is $$LaTeX$$
Default output: "<stem>#ENHANCED.drawio" next to the input (suffix configurable with --suffix).
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from audit_drawio import hex2rgb, is_hex, load_yaml, to_lab  # noqa: E402
from drawio_doc import Doc  # noqa: E402

COLOR_KEYS = ("fillColor", "strokeColor", "fontColor", "gradientColor", "imageBorder", "labelBackgroundColor")


def enhanced_path(path, suffix="#ENHANCED"):
    stem, ext = os.path.splitext(path)
    if stem.endswith(suffix):
        return path
    return stem + suffix + (ext or ".drawio")


class Log:
    def __init__(self):
        self.lines = []

    def __call__(self, msg):
        self.lines.append(msg)
        print("  " + msg)


def pass_colors(doc, theme, log, close_de=10.0, forced=None, add_roles=False, theme_path=None):
    """Bring colors onto the theme WITHOUT erasing meaning.
    1. explicit --map wins;  2. a color within `close_de` (CIELAB dE) of a theme color -> that color;
    3. a fill that is a tint of a theme color (theme color at 5-70 % opacity over the page) -> that
       role + fillOpacity;  4. anything else is kept and reported; with --add-roles it is written to
       the theme as a named role so the figure is explicitly on-theme. Never maps a distinct color
       to the background."""
    pal = {r: c.lower() for r, c in (theme.get("colors") or {}).items()}
    fop = {}                                      # forced opacity for fills: "#hex=role@25"
    fx = {}
    for k, v in (forced or {}).items():
        role, _, op = v.partition("@")
        fx[k.lower()] = pal.get(role, role).lower()
        if op:
            fop[k.lower()] = float(op)
    forced = fx
    labs = {c: to_lab(hex2rgb(c)) for c in set(pal.values())}
    page_bg = hex2rgb(doc.model.get("background")) if is_hex(doc.model.get("background")) else (1, 1, 1)

    def near(h):
        L = to_lab(hex2rgb(h))
        best = min(labs, key=lambda c: math.dist(L, labs[c])) if labs else None
        return best, (math.dist(L, labs[best]) if best else 1e9)

    tint_cache = {}

    def as_tint(h):
        if h in tint_cache:
            return tint_cache[h]
        tint_cache[h] = _as_tint(h)
        return tint_cache[h]

    def _as_tint(h):
        rgb = hex2rgb(h)
        best = None
        for role_hex in labs:
            base = hex2rgb(role_hex)
            if max(abs(x - y) for x, y in zip(base, page_bg)) < 0.05:
                continue
            for a100 in range(5, 71):
                a = a100 / 100
                mix = tuple(a * x + (1 - a) * y for x, y in zip(base, page_bg))
                d = math.dist(to_lab(rgb), to_lab(mix))
                if best is None or d < best[0]:
                    best = (d, role_hex, a100)
        return best if best and best[0] <= close_de else None
    mapped = tinted = 0
    kept = {}
    for c in doc.cells:
        for k in COLOR_KEYS:
            v = c.get(k)
            if not is_hex(v):
                continue
            v = v.lower()
            if v in forced:
                c.set_style(**{k: forced[v]}); mapped += 1
                if k == "fillColor" and v in fop:
                    c.set_style(fillOpacity=round(fop[v] * float(c.get("fillOpacity", 100)) / 100))
                continue
            if v in labs:
                continue
            best, dist = near(v)
            if best and dist <= close_de:
                c.set_style(**{k: best}); mapped += 1; continue
            if k == "fillColor":
                t = as_tint(v)
                if t:
                    prev = float(c.get("fillOpacity", 100)) / 100
                    c.set_style(fillColor=t[1], fillOpacity=round(t[2] * prev)); tinted += 1; continue
            kept[v] = kept.get(v, 0) + 1
        val = c.value
        nv = re.sub(r'(color="?)(#[0-9a-fA-F]{3,6})',
                    lambda m: m.group(1) + (forced.get(m.group(2).lower()) or (near(m.group(2))[0] if near(m.group(2))[1] <= close_de else m.group(2))), val)
        if nv != val:
            c.value = nv; mapped += 1
    bg = (doc.model.get("background") or "").lower()
    if is_hex(bg) and bg not in labs:
        nb = forced.get(bg) or (near(bg)[0] if near(bg)[1] <= close_de else None)
        if nb:
            doc.model.set("background", nb); mapped += 1
        else:
            kept[bg] = kept.get(bg, 0) + 1
    if add_roles and kept and theme_path and theme_path.endswith((".yaml", ".yml")):
        import yaml
        t = yaml.safe_load(open(theme_path, encoding="utf-8"))
        cols = t.setdefault("colors", {})
        existing = {v.lower() for v in cols.values()}
        n = 1
        for h in sorted(kept):
            if h in existing:
                continue
            while f"extra_{n}" in cols:
                n += 1
            cols[f"extra_{n}"] = h; n += 1
        yaml.safe_dump(t, open(theme_path, "w", encoding="utf-8"), sort_keys=False, allow_unicode=True)
        log(f"colors: added {len(kept)} figure-specific colors to the theme as extra_* roles (rename them semantically)")
    log(f"colors: {mapped} snapped to theme colors, {tinted} fills expressed as theme role + opacity"
        + (f"; kept {len(kept)} distinct colors not in the theme: {', '.join(sorted(kept))}" if kept else ""))


def pass_fonts(doc, theme, log, family=None):
    fonts = theme.get("fonts") or {}
    key = theme.get("default_font", "sans")
    fam = family or (fonts.get(key) or {}).get("family", "Helvetica")
    n = 0
    for c in doc.vertices():
        if c.plain and not c.is_math and c.get("fontFamily") != fam:
            c.set_style(fontFamily=fam); n += 1
        if c.value and "font-family" in c.value:
            c.value = re.sub(r"font-family:[^;\"]+;?", "", c.value)
    for e in doc.edges():
        if e.plain and e.get("fontFamily") != fam:
            e.set_style(fontFamily=fam); n += 1
    log(f"fonts: {n} labels set to '{fam}'")


def pass_sizes(doc, theme, brief, log, to_theme=False, merge=0.12, theme_path=None):
    """Harmonize font sizes: merge sizes within `merge` (12 %) into one level (the most used size),
    optionally snap levels to theme size roles (--to-theme: only when the figure was built with this
    theme's scale), then raise anything below the brief's minimum print size."""
    cells = [c for c in doc.cells if c.plain and "fontSize" in c.style]
    count = {}
    for c in cells:
        fs = float(c.get("fontSize")); count[fs] = count.get(fs, 0) + 1
    levels, mapping = [], {}
    for fs in sorted(count):
        if levels and fs <= levels[-1][0] * (1 + merge):
            levels[-1][1].append(fs)
        else:
            levels.append([fs, [fs]])
    for _, members in levels:
        rep = max(members, key=lambda m: (count[m], m))
        for m in members:
            mapping[m] = rep
    roles = sorted({float(v) for v in (theme.get("sizes") or {}).values()})
    if to_theme and roles:
        mapping = {k: min(roles, key=lambda r: abs(r - v)) for k, v in mapping.items()}
    pt_per_px = brief.get("width_in", 7.0) * 72 / max(doc.page[0], 1)
    min_px = brief.get("min_font_pt", 7.0) / pt_per_px
    changed = raised = 0
    bumped = {}
    for c in cells:
        fs = float(c.get("fontSize"))
        nfs = mapping.get(fs, fs)
        if nfs < min_px:
            bumped[nfs] = math.ceil(min_px * 2) / 2
            nfs = bumped[nfs]; raised += 1
        if abs(nfs - fs) > 0.01:
            c.set_style(fontSize=round(nfs, 2)); changed += 1
    if bumped and theme_path and theme_path.endswith((".yaml", ".yml")):
        # keep the theme consistent with the figure: raise the affected size roles too
        import yaml
        t = yaml.safe_load(open(theme_path, encoding="utf-8"))
        for role, val in list((t.get("sizes") or {}).items()):
            if float(val) in bumped:
                t["sizes"][role] = bumped[float(val)]
        yaml.safe_dump(t, open(theme_path, "w", encoding="utf-8"), sort_keys=False, allow_unicode=True)
        log(f"sizes: theme roles updated for the print minimum: {bumped}")
    lv = sorted({mapping[k] for k in mapping})
    log(f"sizes: {len(count)} sizes -> {len(lv)} levels {lv}; {changed} labels changed, {raised} raised to the "
        f"{brief.get('min_font_pt', 7)} pt minimum ({min_px:.1f} px at {brief.get('width_in', 7.0)} in)")


def pass_strokes(doc, theme, log, head=None):
    roles = sorted({float(v) for v in (theme.get("strokes") or {}).values()})
    n = h = 0
    for c in doc.cells:
        if "strokeWidth" in c.style and roles:
            sw = float(c.get("strokeWidth"))
            ns = min(roles, key=lambda r: abs(r - sw))
            if abs(ns - sw) > 0.01:
                c.set_style(strokeWidth=ns); n += 1
        if c.is_edge and head and c.get("endArrow", "classic") not in ("none",) and c.get("shape") != "flexArrow":
            if c.get("endSize") != str(head):
                c.set_style(endSize=head); h += 1
    log(f"strokes: {n} widths snapped to theme roles" + (f", {h} arrow heads set to {head}" if head else ""))


def pass_align(doc, log, tol=3.0):
    shapes = [c for c in doc.vertices() if not c.is_text and not c.is_image and c.abs_geo() and c.abs_geo()[2] >= 14 and c.abs_geo()[3] >= 14]
    moved = 0
    for key in ("center-y", "center-x", "top", "left"):
        f = {"left": lambda g: g[0], "top": lambda g: g[1], "center-x": lambda g: g[0] + g[2] / 2,
             "center-y": lambda g: g[1] + g[3] / 2}[key]
        horiz = key in ("left", "center-x")
        parent = {c.id: c.id for c in shapes}

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]; i = parent[i]
            return i
        for i in range(len(shapes)):
            for j in range(i + 1, len(shapes)):
                a, b = shapes[i].abs_geo(), shapes[j].abs_geo()
                if not (0.01 < abs(f(a) - f(b)) <= tol):
                    continue
                ratio = max(a[2], a[3]) / max(b[2], b[3])
                gap = (max(0, max(a[1], b[1]) - min(a[1] + a[3], b[1] + b[3])) if horiz
                       else max(0, max(a[0], b[0]) - min(a[0] + a[2], b[0] + b[2])))
                contains = lambda p, q: p[0] <= q[0] and p[1] <= q[1] and p[0] + p[2] >= q[0] + q[2] and p[1] + p[3] >= q[1] + q[3]  # noqa: E731
                if 1 / 3 <= ratio <= 3 and gap < 160 and not contains(a, b) and not contains(b, a):
                    parent[find(shapes[i].id)] = find(shapes[j].id)
        groups = {}
        for c in shapes:
            groups.setdefault(find(c.id), []).append(c)
        for members in groups.values():
            if len(members) < 2:
                continue
            vals = sorted(f(m.abs_geo()) for m in members)
            target = vals[len(vals) // 2]
            for m in members:
                g = m.abs_geo(); d = target - f(g)
                if abs(d) > 0.01:
                    m.set_abs_geo(**({"x": g[0] + d} if horiz else {"y": g[1] + d})); moved += 1
    log(f"align: {moved} near-miss alignments snapped (tol {tol}px)")


def pass_attach(doc, log, tol=8.0):
    verts = [v for v in doc.vertices() if not v.is_text and not v.is_image and v.abs_geo() and v.abs_geo()[2] > 1]
    n = 0
    for e in doc.edges():
        for side, ptag in (("source", "sourcePoint"), ("target", "targetPoint")):
            if e.el.get(side):
                continue
            g_el = e.geo_el
            p = next((p for p in (g_el.findall("mxPoint") if g_el is not None else []) if p.get("as") == ptag), None)
            if p is None:
                continue
            x, y = float(p.get("x", 0)), float(p.get("y", 0))
            best = None
            for v in verts:
                g = v.abs_geo()
                inside = g[0] < x < g[0] + g[2] and g[1] < y < g[1] + g[3]
                dist = math.hypot(max(g[0] - x, 0, x - g[0] - g[2]), max(g[1] - y, 0, y - g[1] - g[3]))
                if not inside and dist <= tol and (best is None or dist < best[0]):
                    best = (dist, v)
            if best:
                e.el.set(side, best[1].id)
                g_el.remove(p)
                e.set_style(**{("exitX" if side == "source" else "entryX"): None, ("exitY" if side == "source" else "entryY"): None})
                n += 1
    log(f"attach: {n} free edge ends attached to the shape they touch")


def pass_fit(doc, log, margin=16.0):
    x, y, w, h = doc.content_bbox()
    dx, dy = margin - x, margin - y
    if abs(dx) > 0.01 or abs(dy) > 0.01:
        doc.translate_all(dx, dy)
    doc.set_page(w + 2 * margin, h + 2 * margin)
    log(f"fit-page: content moved by ({dx:.0f}, {dy:.0f}); page = {w + 2 * margin:.0f} x {h + 2 * margin:.0f}")


def pass_math(doc, log):
    has = any(c.is_math for c in doc.vertices())
    if has and not doc.math:
        doc.math = True
        log("math: diagram math flag turned on")
    else:
        log(f"math: {'on' if doc.math else 'off'} ({sum(c.is_math for c in doc.vertices())} LaTeX labels)")


def run(src, out=None, theme=None, brief=None, **opts):
    doc = Doc.load(src)
    th = load_yaml(theme) if isinstance(theme, str) else (theme or {})
    br = load_yaml(brief) if isinstance(brief, str) else (brief or {})
    br = br.get("target", br)
    log = Log()
    if opts.get("colors"): pass_colors(doc, th, log, opts.get("max_de", 10.0), opts.get("map"), opts.get("add_roles"),
                                       theme if isinstance(theme, str) else None)
    if opts.get("fonts"): pass_fonts(doc, th, log, opts.get("family"))
    if opts.get("sizes"): pass_sizes(doc, th, br, log, opts.get("to_theme", False),
                                     theme_path=theme if isinstance(theme, str) and opts.get("update_theme") else None)
    if opts.get("strokes"): pass_strokes(doc, th, log, opts.get("head"))
    if opts.get("attach"): pass_attach(doc, log, opts.get("attach_tol", 8.0))
    if opts.get("align"): pass_align(doc, log, opts.get("tol", 3.0))
    if opts.get("fit_page") is not None: pass_fit(doc, log, opts["fit_page"])
    if opts.get("math"): pass_math(doc, log)
    out = out or enhanced_path(src, opts.get("suffix", "#ENHANCED"))
    doc.save(out)
    return out, log.lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("drawio"); ap.add_argument("-o", "--out")
    ap.add_argument("--theme"); ap.add_argument("--brief")
    ap.add_argument("--suffix", default="#ENHANCED")
    for f in ("colors", "fonts", "sizes", "strokes", "align", "attach", "math", "all"):
        ap.add_argument("--" + f, action="store_true")
    ap.add_argument("--fit-page", type=float, default=None)
    ap.add_argument("--to-theme", action="store_true", help="with --sizes: snap size levels to theme roles")
    ap.add_argument("--update-theme", action="store_true", help="with --sizes: write raised sizes back into the theme")
    ap.add_argument("--add-roles", action="store_true", help="with --colors: add kept colors to the theme as extra_* roles")
    ap.add_argument("--max-de", type=float, default=10.0, help="CIELAB distance treated as 'same color'"); ap.add_argument("--map", action="append", default=[])
    ap.add_argument("--family"); ap.add_argument("--head", type=float); ap.add_argument("--tol", type=float, default=3.0)
    ap.add_argument("--attach-tol", type=float, default=8.0); ap.add_argument("--log", help="append changes to this markdown file")
    a = ap.parse_args()
    if a.all:
        a.colors = a.fonts = a.sizes = a.strokes = a.align = a.attach = a.math = True
        a.fit_page = 16 if a.fit_page is None else a.fit_page
    forced = dict(m.split("=", 1) for m in a.map)
    print("enhance passes:")
    out, lines = run(a.drawio, a.out, a.theme, a.brief, colors=a.colors, fonts=a.fonts, sizes=a.sizes, strokes=a.strokes,
                     align=a.align, attach=a.attach, math=a.math, fit_page=a.fit_page, max_de=a.max_de, map=forced,
                     family=a.family, head=a.head, to_theme=a.to_theme, update_theme=a.update_theme, add_roles=a.add_roles, tol=a.tol, attach_tol=a.attach_tol, suffix=a.suffix)
    if a.log:
        with open(a.log, "a", encoding="utf-8") as fh:
            fh.write(f"\n### enhance.py on `{os.path.basename(a.drawio)}`\n" + "".join(f"- {l}\n" for l in lines))
    print("wrote", out)


if __name__ == "__main__":
    main()
