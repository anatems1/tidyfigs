#!/usr/bin/env python3
"""
audit_drawio.py — is this figure ready for an academic article?

    python audit_drawio.py fig.drawio [--brief brief.yaml] [--theme theme.yaml] [--out-dir DIR] [--tag before]

Checks (all at the TARGET PRINT SIZE from the brief: width_in, min_font_pt, grayscale, colorblind):
  legibility   font sizes in pt at print size, hairline strokes, low-resolution embedded images
  color        palette size, off-theme colors, text contrast (WCAG), grayscale and color-vision-
               deficiency (deuteranopia / protanopia) separability of category fills
  typography   number of font families / sizes, sizes not in theme
  math         math flag, LaTeX that fails to parse, Unicode math in plain labels (inconsistent notation)
  layout       lint (overlaps, overflow, near-miss alignment, uneven gaps), margins, excess whitespace,
               aspect ratio vs column, in-figure titles, long labels, density
  connectors   dangling edge ends next to shapes, stroke / arrow-head variety
Writes <tag>_audit.md, <tag>_audit.json and <tag>_print_preview.png (actual print size at 150 dpi).
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import base64
import io
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from drawio_doc import Doc  # noqa: E402

DEFAULT_BRIEF = dict(width_in=7.0, min_font_pt=7.0, grayscale=False, colorblind=True)
CVD = {"deuteranopia": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
       "protanopia": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]}
UNICODE_MATH = "λθαβγδεσμπρτφωΣΔΩ∑∏∫≤≥≠≈×÷∈∉∞√∂∇±→⇒"


def load_yaml(p):
    if not p or not os.path.exists(p):
        return {}
    if p.endswith((".yaml", ".yml")):
        import yaml
        return yaml.safe_load(open(p, encoding="utf-8")) or {}
    if p.endswith(".json"):
        return json.load(open(p, encoding="utf-8"))
    import tomllib
    return tomllib.loads(open(p, encoding="utf-8").read())


# ---------------- color helpers
def hex2rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def delin(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def luminance(rgb):
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def to_lab(rgb):
    r, g, b = (lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116  # noqa: E731
    return (116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z)))


def de(a, b):
    return math.dist(to_lab(a), to_lab(b))


def simulate(rgb, kind):
    m = CVD[kind]
    l = [lin(c) for c in rgb]
    return tuple(delin(sum(m[i][j] * l[j] for j in range(3))) for i in range(3))


def blend(rgb, alpha, bg=(1, 1, 1)):
    return tuple(alpha * c + (1 - alpha) * b for c, b in zip(rgb, bg))


def is_hex(v):
    return bool(v) and re.fullmatch(r"#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?", v.strip()) is not None


# ---------------- audit
def category_count(path):
    """Distinct effective fill colors (opacity applied, dE >= 8 apart) — a proxy for color-coded categories."""
    doc = Doc.load(path)
    page_bg = hex2rgb(doc.model.get("background")) if is_hex(doc.model.get("background")) else (1, 1, 1)
    reps = []
    for c in doc.vertices():
        f = c.get("fillColor")
        if not is_hex(f) or c.is_text:
            continue
        a = float(c.get("fillOpacity", 100)) / 100 * float(c.get("opacity", 100)) / 100
        eff = blend(hex2rgb(f), a, page_bg)
        if contrast(eff, page_bg) < 1.04:
            continue
        if all(de(eff, r) >= 8 for r in reps):
            reps.append(eff)
    return len(reps)


def audit(path, brief=None, theme_path=None, accepted=(), reference=None):
    b = dict(DEFAULT_BRIEF); b.update({k: v for k, v in (brief or {}).items() if v is not None})
    doc = Doc.load(path)
    pw, ph = doc.page
    cb = doc.content_bbox()
    fig_w = max(cb[2], 1)
    pt_per_px = b["width_in"] * 72 / max(pw, 1)
    issues = {k: [] for k in ("legibility", "color", "typography", "math", "layout", "connectors")}
    stats = {}
    page_bg = hex2rgb(doc.model.get("background")) if is_hex(doc.model.get("background")) else (1, 1, 1)

    # --- legibility
    sizes, fams = {}, {}
    for c in doc.vertices():
        if not c.plain or c.is_group:
            continue
        fs = float(c.get("fontSize", 11))
        sizes[fs] = sizes.get(fs, 0) + 1
        if not c.is_math:
            fams[c.get("fontFamily", "Helvetica")] = fams.get(c.get("fontFamily", "Helvetica"), 0) + 1
        pt = fs * pt_per_px * (1.0 if not c.is_math else 1.0)
        if pt < b["min_font_pt"] - 0.05:
            issues["legibility"].append(f"{c.id}: '{c.plain[:30]}' is {pt:.1f} pt at {b['width_in']} in wide (min {b['min_font_pt']} pt)")
    for c in doc.cells:
        sw = float(c.get("strokeWidth", 1)) if (c.is_edge or (c.is_vertex and c.get("strokeColor") not in (None, "none"))) else None
        if sw is not None and sw * pt_per_px < 0.45 and not c.is_text:
            issues["legibility"].append(f"{c.id}: stroke {sw:g}px = {sw * pt_per_px:.2f} pt (< 0.5 pt hairline)")
            break
    for c in doc.vertices():
        if c.is_image:
            m = re.match(r"data:image/(png|jpeg|jpg|webp),(.+)", c.get("image", ""), re.S)
            if m:
                try:
                    from PIL import Image
                    im = Image.open(io.BytesIO(base64.b64decode(m.group(2))))
                    g = c.abs_geo()
                    printed_in = g[2] * pt_per_px / 72
                    dpi = im.width / max(printed_in, 1e-6)
                    if dpi < 300:
                        issues["legibility"].append(f"{c.id}: embedded raster is {dpi:.0f} dpi at print size (journals want >= 300)")
                except Exception:
                    pass

    # --- color
    th = load_yaml(theme_path) if theme_path else {}
    palette = {v.lower() for v in (th.get("colors") or {}).values()}
    used = {}
    for c in doc.cells:
        for k in ("fillColor", "strokeColor", "fontColor", "gradientColor"):
            v = c.get(k)
            if is_hex(v):
                used[v.lower()] = used.get(v.lower(), 0) + 1
        for m in re.finditer(r'color="?(#[0-9a-fA-F]{3,6})', c.value):
            used[m.group(1).lower()] = used.get(m.group(1).lower(), 0) + 1
    stats["colors_used"] = used
    chromatic = [h for h in used if max(hex2rgb(h)) - min(hex2rgb(h)) > 0.08]
    if len(chromatic) > 4:
        issues["color"].append(f"{len(chromatic)} distinct hues ({', '.join(sorted(chromatic))}); academic figures read best with <= 3 hues + tints")
    if palette:
        off = sorted(h for h in used if h not in palette)
        if off:
            issues["color"].append(f"off-theme colors: {', '.join(off)}")
    # category fills (effective color after opacity)
    fills = {}
    for c in doc.vertices():
        f = c.get("fillColor")
        if not is_hex(f) or c.is_text:
            continue
        a = float(c.get("fillOpacity", 100)) / 100 * float(c.get("opacity", 100)) / 100
        eff = blend(hex2rgb(f), a, page_bg)
        if contrast(eff, page_bg) < 1.08:
            continue
        key = "#%02x%02x%02x" % tuple(round(x * 255) for x in eff)
        fills.setdefault(key, []).append(c.id)
    keys = sorted(fills)
    stats["category_fills"] = {k: len(v) for k, v in fills.items()}
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            A, B = hex2rgb(keys[i]), hex2rgb(keys[j])
            if de(A, B) < 8:
                continue
            if b.get("grayscale") and abs(to_lab(A)[0] - to_lab(B)[0]) < 12:
                issues["color"].append(f"fills {keys[i]} and {keys[j]} differ by only {abs(to_lab(A)[0] - to_lab(B)[0]):.0f} L* in grayscale "
                                       f"(e.g. {fills[keys[i]][0]} vs {fills[keys[j]][0]}) — add pattern/outline or change lightness")
            if b.get("colorblind"):
                for kind in CVD:
                    d2 = de(simulate(A, kind), simulate(B, kind))
                    if d2 < 8:
                        issues["color"].append(f"fills {keys[i]} vs {keys[j]} nearly identical under {kind} (dE {d2:.1f})")
                        break
    if reference and os.path.exists(reference):
        before, after = category_count(reference), category_count(path)
        stats["category_colors"] = {"before": before, "after": after}
        if after < before:
            issues["color"].append(f"color-coded categories dropped from {before} to {after} distinct fills vs the original — "
                                   "a color pass or edit erased a distinction (restore it or confirm it was intended)")
    # text contrast
    verts = [c for c in doc.vertices() if c.abs_geo()]
    for c in verts:
        if not c.plain or c.is_math and False:
            continue
        fc = c.get("fontColor", "#000000")
        if not is_hex(fc):
            continue
        g = c.abs_geo()
        bgc = None
        if is_hex(c.get("fillColor")) and not c.is_text:
            a = float(c.get("fillOpacity", 100)) / 100
            bgc = blend(hex2rgb(c.get("fillColor")), a, page_bg)
        else:
            cx, cy = g[0] + g[2] / 2, g[1] + g[3] / 2
            best = None
            for o in verts:
                if o is c or not is_hex(o.get("fillColor")) or o.is_text or o.is_image:
                    continue
                og = o.abs_geo()
                if og[0] <= cx <= og[0] + og[2] and og[1] <= cy <= og[1] + og[3]:
                    if best is None or og[2] * og[3] < best[0]:
                        best = (og[2] * og[3], o)
            if best:
                o = best[1]
                bgc = blend(hex2rgb(o.get("fillColor")), float(o.get("fillOpacity", 100)) / 100, page_bg)
        bgc = bgc or page_bg
        ratio = contrast(hex2rgb(fc), bgc)
        big = float(c.get("fontSize", 11)) * pt_per_px >= 14 or (int(float(c.get("fontStyle", 0))) & 1)
        if ratio < (3.0 if big else 4.5):
            issues["color"].append(f"{c.id}: text contrast {ratio:.1f}:1 ('{c.plain[:25]}', {fc} on {'#%02x%02x%02x' % tuple(round(x * 255) for x in bgc)})")

    # --- typography
    stats["font_families"] = fams; stats["font_sizes"] = sizes
    if len(fams) > 2:
        issues["typography"].append(f"{len(fams)} font families: {', '.join(fams)} (use 1, at most 2)")
    if len(sizes) > 6:
        issues["typography"].append(f"{len(sizes)} distinct font sizes {sorted(sizes)} (use <= 5-6 roles)")
    if th.get("sizes"):
        roles = {float(v) for v in th["sizes"].values()}
        odd = sorted(s for s in sizes if s not in roles)
        if odd:
            issues["typography"].append(f"font sizes not in theme: {odd}")

    # --- math
    mlabels = [c for c in doc.vertices() if c.is_math]
    inline = [c for c in doc.vertices() if not c.is_math and re.search(r"\\\(.+?\\\)", c.plain)]
    stats["math_labels"] = len(mlabels); stats["inline_math_labels"] = len(inline)
    if (mlabels or inline) and not doc.math:
        issues["math"].append("labels contain $$…$$ but the diagram math flag is off (draw.io shows raw LaTeX)")
    try:
        from drawio_kit import render_math
        for c in mlabels:
            src = re.fullmatch(r"\s*\$\$(.+)\$\$\s*", c.plain, re.S).group(1)
            if render_math(src, 20) is None:
                issues["math"].append(f"{c.id}: LaTeX may not render: {src[:50]}")
    except Exception:
        pass
    uni = [c for c in doc.vertices() if c.plain and not c.is_math and any(ch in UNICODE_MATH for ch in c.plain)]
    if uni and (mlabels or inline):
        issues["math"].append(f"{len(uni)} plain labels use Unicode math ({', '.join(sorted({ch for c in uni for ch in c.plain if ch in UNICODE_MATH}))}) "
                              f"while {len(mlabels)} use LaTeX — make notation consistent (e.g. {uni[0].id})")
    elif uni:
        issues["math"].append(f"{len(uni)} labels write math in Unicode ({uni[0].id}: '{uni[0].plain[:25]}'); consider $$LaTeX$$ labels matching the paper")

    # --- layout
    try:
        from lint_drawio import lint
        L = lint(path, theme_path)
        # off-theme values are already reported under color / typography
        issues["layout"] += [f"lint: {w}" for w in L["errors"] + L["warnings"] if not w.startswith("off-theme")]
    except Exception as e:
        issues["layout"].append(f"lint failed: {e}")
    m = [cb[0], cb[1], pw - cb[0] - cb[2], ph - cb[1] - cb[3]]
    stats["margins"] = [round(v, 1) for v in m]
    if min(m) < 6:
        issues["layout"].append(f"content touches the page edge (margins l,t,r,b = {[round(v) for v in m]})")
    if m[0] + m[2] > 0.2 * pw or m[1] + m[3] > 0.2 * ph:
        issues["layout"].append(f"excess page whitespace (margins {[round(v) for v in m]}) — fit page to content")
    aspect = cb[3] / max(cb[2], 1)
    stats["aspect_h_over_w"] = round(aspect, 2)
    if b["width_in"] <= 3.6 and aspect > 1.3:
        issues["layout"].append(f"tall figure (h/w = {aspect:.2f}) for a single column; consider a wider layout")
    if b["width_in"] >= 6 and aspect < 0.25:
        issues["layout"].append(f"very flat figure (h/w = {aspect:.2f}); text will be small when scaled to width")
    texts = [c for c in doc.vertices() if c.plain and not c.is_math]
    stats["text_items"] = len(texts)
    if len(texts) > 35:
        issues["layout"].append(f"{len(texts)} text items — dense; move explanations to the caption")
    for c in texts:
        if len(c.plain.split()) > 16:
            issues["layout"].append(f"{c.id}: long label ({len(c.plain.split())} words) — shorten or move to caption")
    if texts:
        top = [c for c in texts if c.abs_geo()[1] < cb[1] + 0.08 * cb[3]]
        mx = max(float(c.get("fontSize", 11)) for c in texts)
        for c in top:
            if float(c.get("fontSize", 11)) >= mx and float(c.get("fontSize", 11)) >= 1.3 * sorted(sizes)[len(sizes) // 2] \
                    and len(c.plain.split()) >= 3 and c.abs_geo()[2] > 0.5 * cb[2]:
                issues["layout"].append(f"{c.id}: in-figure title '{c.plain[:40]}' — journals put titles in the caption")

    # --- connectors
    sws, heads = {}, {}
    for e in doc.edges():
        sws[e.get("strokeWidth", "1")] = 1
        if e.get("endArrow", "classic") != "none":
            heads[e.get("endSize", "6")] = 1
        for side, ptag in (("source", "sourcePoint"), ("target", "targetPoint")):
            if e.el.get(side):
                continue
            p = next((p for p in e.el.iter("mxPoint") if p.get("as") == ptag), None)
            if p is None:
                continue
            x, y = float(p.get("x", 0)), float(p.get("y", 0))
            for v in verts:
                if v.is_text or v.is_group or v.is_image:
                    continue
                g = v.abs_geo()
                dx = max(g[0] - x, 0, x - g[0] - g[2]); dy = max(g[1] - y, 0, y - g[1] - g[3])
                inside = g[0] < x < g[0] + g[2] and g[1] < y < g[1] + g[3]
                if (math.hypot(dx, dy) <= 8 and not inside and g[2] > 1 and g[3] > 1):
                    issues["connectors"].append(f"{e.id}: free {side} end ({x:.0f},{y:.0f}) is {math.hypot(dx, dy):.0f}px from {v.id} — attach it")
                    break
    if len(sws) > 3:
        issues["connectors"].append(f"{len(sws)} different edge stroke widths {sorted(sws, key=float)} (use 2-3 roles)")
    if len(heads) > 2:
        issues["connectors"].append(f"{len(heads)} arrow-head sizes {sorted(heads, key=float)}")

    accepted = [x for x in (accepted or []) if x]
    ignored = 0
    if accepted:
        for k in issues:
            keep = [x for x in issues[k] if not any(s in x for s in accepted)]
            ignored += len(issues[k]) - len(keep); issues[k] = keep
    stats["accepted_ignored"] = ignored
    status = {k: ("pass" if not v else "warn" if len(v) <= 3 else "fail") for k, v in issues.items()}
    n = sum(len(v) for v in issues.values())
    score = max(0, 100 - sum(min(len(v), 8) * w for (k, v), w in zip(issues.items(), (4, 3, 2, 4, 2, 2))))
    return dict(file=path, brief=b, pt_per_px=round(pt_per_px, 3), issues=issues, status=status, stats=stats,
                score=score, n_issues=n)


def write_report(r, out_dir, tag):
    os.makedirs(out_dir, exist_ok=True)
    b = r["brief"]
    md = [f"# Audit ({tag}): `{os.path.basename(r['file'])}`", "",
          f"Target: **{b['width_in']} in** wide, min font **{b['min_font_pt']} pt**, grayscale-safe: {b.get('grayscale')}, "
          f"colorblind-safe: {b.get('colorblind')}  (1 px = {r['pt_per_px']} pt)", "",
          f"**Readiness score: {r['score']}/100**  ({r['n_issues']} issues)", "",
          "| area | status | issues |", "|---|---|---|"]
    for k, v in r["issues"].items():
        md.append(f"| {k} | {r['status'][k]} | {len(v)} |")
    for k, v in r["issues"].items():
        if v:
            md += ["", f"## {k}", ""] + [f"- {x}" for x in v[:40]] + ([f"- … {len(v) - 40} more"] if len(v) > 40 else [])
    s = r["stats"]
    md += ["", "## stats", "", f"- font families: {s.get('font_families')}", f"- font sizes: {s.get('font_sizes')}",
           f"- colors used: {s.get('colors_used')}", f"- margins l,t,r,b: {s.get('margins')}; h/w = {s.get('aspect_h_over_w')}",
           f"- text items: {s.get('text_items')}; math labels: {s.get('math_labels')} (+{s.get('inline_math_labels', 0)} with inline math)",
           f"- accepted warnings ignored (brief review.accepted_warnings): {s.get('accepted_ignored', 0)}"]
    p = os.path.join(out_dir, f"{tag}_audit.md")
    open(p, "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(r, open(os.path.join(out_dir, f"{tag}_audit.json"), "w", encoding="utf-8"), indent=1, default=str)
    return p


def print_preview(path, out_dir, tag, width_in, dpi=150):
    from render_preview import render_kit
    out = os.path.join(out_dir, f"{tag}_print_preview.png")
    render_kit(path, out, scale=2.0, width=int(width_in * dpi))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("drawio"); ap.add_argument("--brief"); ap.add_argument("--theme")
    ap.add_argument("--out-dir", default="."); ap.add_argument("--tag", default="audit")
    ap.add_argument("--width-in", type=float); ap.add_argument("--min-pt", type=float)
    ap.add_argument("--reference", help="original .drawio: report lost color categories")
    a = ap.parse_args()
    br = load_yaml(a.brief) if a.brief else {}
    br = br.get("target", br) if isinstance(br, dict) else {}
    if a.width_in: br["width_in"] = a.width_in
    if a.min_pt: br["min_font_pt"] = a.min_pt
    full = load_yaml(a.brief) if a.brief else {}
    r = audit(a.drawio, br, a.theme, (full.get("review") or {}).get("accepted_warnings", []), a.reference)
    p = write_report(r, a.out_dir, a.tag)
    pp = print_preview(a.drawio, a.out_dir, a.tag, r["brief"]["width_in"])
    print(f"score {r['score']}/100, {r['n_issues']} issues: " + ", ".join(f"{k} {len(v)}" for k, v in r["issues"].items()))
    for k, v in r["issues"].items():
        for x in v[:6]:
            print(f"  [{k}] {x}")
    print("wrote", p, "and", pp)


if __name__ == "__main__":
    main()
