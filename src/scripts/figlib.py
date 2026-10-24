"""
figlib — reusable academic-figure components built on drawio_kit.

Every function draws onto a Diagram `d` (source px coordinates, theme roles for colors/sizes) and
returns ids / geometry so you can connect things. Import in build.py:  `from figlib import *`

Style presets (dicts for d.rect(**NODE) etc.):
    NODE   white box, primary outline          — default step / entity
    SOFT   secondary tint, secondary outline   — second category (e.g. online, mechanisms)
    DARK   primary fill, white text            — emphasis (outputs, key results, expert step)
    MUTED  neutral tint, dashed outline        — context / moderators / optional
    GHOST  no fill, dashed neutral outline     — group frames
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import math

from drawio_kit import measure_math

NODE = dict(fill="background", stroke="primary", sw="normal", rounded=True, size="body")
SOFT = dict(fill="secondary", fill_opacity="tint", stroke="secondary", sw="normal", rounded=True, size="body")
DARK = dict(fill="primary", stroke="primary", color="background", rounded=True, size="body")
MUTED = dict(fill="neutral", fill_opacity="tint", stroke="neutral", sw="normal", rounded=True, size="body", dashed=True)
GHOST = dict(fill="none", stroke="neutral", sw="thin", rounded=10, dashed=True)

__all__ = ["NODE", "SOFT", "DARK", "MUTED", "GHOST", "style", "pill", "lane", "chain", "cycle", "layers",
           "frame", "bracket", "spread", "annotated_equation", "rating_dots", "rating_legend", "card",
           "continuum", "legend", "badge", "axes", "table", "connect", "eq"]


def style(base, **over):
    """Copy a preset with overrides: style(NODE, size="label")."""
    s = dict(base); s.update(over); return s


def pill(d, cx, y, text, w=200, h=34, fill="primary", color="background", size="subheading", id=None):
    """Rounded header pill (column / stage heading)."""
    return d.rect(cx - w / 2, y, w, h, f"**{text}**", fill=fill, stroke=fill, color=color, rounded=h / 2, size=size, id=id)


def badge(d, cx, cy, n, r=13, fill="primary", color="background", id=None):
    """Numbered circle (step numbers)."""
    return d.circle(cx, cy, r, f"**{n}**", fill=fill, stroke="background", color=color, size="small", id=id)


def lane(d, x, y, w, h, title, band_w=38, band="primary", wash="neutral", id=None):
    """Swimlane: washed background + rotated title band on the left. Returns content box."""
    d.rect(x, y, w, h, fill=wash, fill_opacity="wash", stroke="neutral", sw="thin", rounded=6, id=id)
    d.rect(x, y, band_w, h, fill=band, stroke=band, rounded=6)
    d.text(f"**{title}**", x + band_w / 2, y + h / 2, size="subheading", color="background", rotation=-90)
    return (x + band_w, y, w - band_w, h)


def connect(d, a, b, side="h", color="primary", sw="thick", **kw):
    """Attach an arrow a->b leaving/entering mid-sides: side 'h' (right->left) or 'v' (bottom->top)."""
    ex, en = ((1, .5), (0, .5)) if side == "h" else ((.5, 1), (.5, 0))
    return d.edge(kw.pop("pts", []), src=a, tgt=b, color=color, sw=sw, exit=ex, entry=en, **kw)


def chain(d, labels, x, y, w, h, gap=30, styles=None, ids=None, direction="h", arrows=True,
          arrow_color="primary", arrow_sw="thick", shapes=None):
    """Row (direction='h') or column ('v') of equal boxes joined by arrows.
    styles: one preset for all or a list per box; shapes: optional list of SHAPES names per box.
    Returns list of ids (in order)."""
    n = len(labels)
    boxes = d.row(x, y, n, w, h, gap) if direction == "h" else d.column(x, y, n, w, h, gap)
    styles = styles if isinstance(styles, list) else [styles or NODE] * n
    ids = ids or [None] * n
    out = []
    for i, ((bx, by, bw, bh), t) in enumerate(zip(boxes, labels)):
        kw = dict(styles[i])
        if shapes and shapes[i]:
            kw["shape"] = shapes[i]
        out.append(d.rect(bx, by, bw, bh, t, id=ids[i], **kw))
    if arrows:
        for a, b in zip(out, out[1:]):
            connect(d, a, b, "h" if direction == "h" else "v", color=arrow_color, sw=arrow_sw)
    return out


def cycle(d, labels, cx, cy, rx, ry, w=156, h=60, styles=None, badges=True, start_deg=-90, close=True,
          close_color="secondary", close_dashed=True, bulge=1.22, arrow_color="primary"):
    """Boxes evenly placed on an ellipse with curved arrows between neighbours (clockwise).
    The closing arrow (last -> first) can be styled separately (feedback). Returns (ids, centers)."""
    n = len(labels)
    styles = styles if isinstance(styles, list) else [styles or NODE] * n
    ids, pos = [], []
    for i, t in enumerate(labels):
        a = math.radians(start_deg) + i * 2 * math.pi / n
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        pos.append((x, y))
        ids.append(d.rect(x - w / 2, y - h / 2, w, h, t, id=f"cyc{i}", **styles[i]))
        if badges:
            badge(d, x - w / 2, y - h / 2, i + 1)
    for i in range(n if close else n - 1):
        j = (i + 1) % n
        (x1, y1), (x2, y2) = pos[i], pos[j]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ctrl = (cx + (mx - cx) * bulge, cy + (my - cy) * bulge)   # control point outside the chord
        last = close and i == n - 1
        d.edge([ctrl], src=ids[i], tgt=ids[j], route="curved", color=close_color if last else arrow_color,
               sw="thick", dashed=last and close_dashed)
    return ids, pos


def layers(d, x, y, w, spec, layer_h=92, gap=26, tab_w=150, comp_h=56, comp_gap=40, styles=None,
           flow_arrows=True, last_highlight=True):
    """Stacked architecture layers. spec = [(layer_name, [component labels...]), ...].
    Components in a layer are joined left->right; a down arrow links consecutive layers.
    styles: optional {layer_index: preset}. Returns {(li, ci): id} and the list of layer boxes."""
    ids, boxes_out = {}, []
    for li, (name, comps) in enumerate(spec):
        ly = y + li * (layer_h + gap)
        last = last_highlight and li == len(spec) - 1
        d.rect(x, ly, w, layer_h, fill="secondary" if last else "neutral", fill_opacity="wash", stroke="neutral",
               sw="thin", rounded=6)
        tab = "secondary" if last else "primary"
        d.rect(x, ly, tab_w, layer_h, f"**{name}**", fill=tab, stroke=tab, color="background", size="subheading", rounded=6)
        cb = d.fit_row(x + tab_w + 25, x + w - 25, ly + (layer_h - comp_h) / 2, len(comps), comp_h, gap=comp_gap)
        st = (styles or {}).get(li, NODE)
        for ci, ((bx, by, bw, bh), t) in enumerate(zip(cb, comps)):
            ids[(li, ci)] = d.rect(bx, by, bw, bh, t, id=f"L{li}c{ci}", **st)
        for ci in range(len(comps) - 1):
            connect(d, ids[(li, ci)], ids[(li, ci + 1)])
        if flow_arrows and li < len(spec) - 1:
            mx = cb[len(cb) // 2][0] + cb[len(cb) // 2][2] / 2
            d.arrow([(mx, ly + layer_h + 2), (mx, ly + layer_h + gap - 2)], color="primary", sw="heavy", head_size=5)
        boxes_out.append((x, ly, w, layer_h))
    return ids, boxes_out


def frame(d, x, y, w, h, color="neutral", id=None, label=None):
    """Dashed group frame (no fill) — e.g. around a column of related items; connect arrows to it."""
    fid = d.rect(x, y, w, h, fill="none", stroke=color, sw="thin", dashed=True, rounded=10, id=id)
    if label:
        d.text(f"*{label}*", x + 8, y - 10, anchor="w", size="small", color=color)
    return fid


def bracket(d, x0, x1, y, color="primary", up=False, tick=8, sw="thick"):
    """Horizontal bracket under (or over, up=True) a span; returns its midpoint x."""
    t = -tick if up else tick
    d.line([(x0, y - t), (x0, y), (x1, y), (x1, y - t)], color=color, sw=sw)
    return (x0 + x1) / 2


def spread(centers, width, gap, lo, hi):
    """Shift box centers left->right so boxes of `width` don't overlap and stay inside [lo, hi]."""
    out = []
    for c in centers:
        c = max(c, lo + width / 2)
        if out and c - out[-1] < width + gap:
            c = out[-1] + width + gap
        out.append(c)
    over = (out[-1] + width / 2 - hi) if out else 0
    return [c - max(0, over) for c in out]


def eq(d, latex, x, y, **kw):
    """Shorthand for d.equation (LaTeX label)."""
    return d.equation(latex, x, y, **kw)


def annotated_equation(d, terms, cx, cy, notes_above=(), notes_below=(), size="equation", term_gap=10,
                       box_w=230, box_h=78, top_y=30, bottom_y=320, lo=30, hi=None, bracket_offset=34):
    """Equation split into terms, each its own LaTeX label, with bracketed callouts.
    terms: [(latex, color_role), ...] in reading order.
    notes_above / notes_below: [(term_index, color_role, markup_text), ...].
    Callout boxes are spread so they never overlap. Returns list of (x0, x1) spans per term."""
    hi = hi or d.width - 30
    sz = d.theme.size(size)
    widths = [measure_math(t, sz)[0] * 1.08 + 6 for t, _ in terms]
    total = sum(widths) + term_gap * (len(terms) - 1)
    x = cx - total / 2
    spans = []
    for (t, col), w in zip(terms, widths):
        d.equation(t, x, cy, w=w, h=sz * 1.9, anchor="w", size=size, color=col)
        spans.append((x, x + w)); x += w + term_gap
    for row, up in ((list(notes_above), True), (list(notes_below), False)):
        if not row:
            continue
        mids = [(spans[i][0] + spans[i][1]) / 2 for i, _, _ in row]
        centers = spread(mids, box_w, 24, lo, hi)
        for (i, col, txt), mx, bx in zip(row, mids, centers):
            x0, x1 = spans[i]
            by = cy - bracket_offset if up else cy + bracket_offset
            bracket(d, x0 + 2, x1 - 2, by, col, up=up)
            top = top_y if up else bottom_y
            yconn = top + box_h if up else top
            ym = (by + yconn) / 2
            d.line([(mx, by), (mx, ym), (bx, ym), (bx, yconn)], color=col, sw="thin")
            d.rect(bx - box_w / 2, top, box_w, box_h, txt, fill="background", stroke=col, sw="normal",
                   rounded=True, size="label")
    return spans


def rating_dots(d, cx, cy, n, of=3, r=7, gap=22, color="primary"):
    """n of `of` filled dots centered at (cx, cy) — Harvey-ball style ordinal rating."""
    for k in range(of):
        d.circle(cx + (k - (of - 1) / 2) * gap, cy, r, fill=color if k < n else "background", stroke=color, sw="normal")


def rating_legend(d, x, y, of=3, best="most favourable", worst="least favourable"):
    rating_dots(d, x + 14, y, of, of, r=5, gap=14)
    d.text(best, x + 14 + of * 9 + 10, y, anchor="w", size="small")
    x2 = x + 190
    rating_dots(d, x2 + 14, y, 1, of, r=5, gap=14)
    d.text(worst, x2 + 14 + of * 9 + 10, y, anchor="w", size="small")


def card(d, x, y, w, h, title, intro=None, sections=(), footer=None, header_fill="primary", id=None):
    """Card with a header band, optional italic intro, bullet sections and a tinted footer.
    sections: [(heading, [items], color_role, marker), ...] e.g. ("Strengths", [...], "secondary", "+")."""
    with d.group(id or f"card_{title.split()[0].lower()}") as gid:
        d.rect(x, y, w, h, fill="background", stroke="neutral", sw="thin", rounded=12, shadow=True)
        d.rect(x, y, w, 54, f"**{title}**", fill=header_fill, stroke=header_fill, color="background", rounded=12, size="heading")
        cy = y + 84
        if intro:
            d.text(f"*{intro}*", x + 18, cy, anchor="w", w=w - 36, h=40, wrap=True, size="label")
            cy += 46
        for head, items, col, mark in sections:
            d.text(f"**{head}**", x + 18, cy, anchor="w", size="body", color=col)
            cy += 28
            for it in items:
                d.text(f"{{{col}|**{mark}**}}  {it}", x + 18, cy, anchor="w", size="label")
                cy += 26
            cy += 20
        if footer:
            d.rect(x + 14, y + h - 84, w - 28, 70, footer, fill="secondary", fill_opacity="tint", stroke="none",
                   rounded=8, size="label")
    return gid


def continuum(d, x0, x1, y, left, right, left_eq=None, right_eq=None, marker=None, marker_label=None,
              colors=("neutral", "secondary")):
    """Horizontal gradient bar with end labels (optionally LaTeX) and an optional marker at fraction `marker`."""
    d.rect(x0, y - 8, x1 - x0, 16, fill=colors[0], gradient=colors[1], gradient_dir="east", stroke="none", rounded=8)
    for x, lab, eq in ((x0, left, left_eq), (x1, right, right_eq)):
        if eq:
            d.equation(eq, x, y + 34, size="eq_small", color="primary")
        d.text(lab, x, y + (62 if eq else 30), size="small")
    if marker is not None:
        xb = x0 + marker * (x1 - x0)
        d.shape("triangle_down", xb - 11, y - 36, 22, 18, fill="primary", stroke="primary")
        if marker_label:
            d.text(marker_label, xb, y - 50, size="small", color="primary")


def legend(d, x, y, items, spacing=190, sw=22, sh=16):
    """items: [(preset_dict, label), ...] drawn left->right."""
    for k, (st, lab) in enumerate(items):
        xx = x + k * spacing
        d.rect(xx, y - sh / 2, sw, sh, **{kk: v for kk, v in st.items() if kk not in ("size", "bold", "color")})
        d.text(lab, xx + sw + 8, y, anchor="w", size="label")


def axes(d, ox, oy, x1, y1, xlabel=None, ylabel=None, xticks=(), yticks=(), color="text", wash=True):
    """Qualitative/quantitative axes with arrowheads. ticks: [(position_px, label), ...]."""
    if wash:
        d.rect(ox, y1, x1 - ox, oy - y1, fill="neutral", fill_opacity="wash", stroke="none")
    d.arrow([(ox, oy), (x1 + 20, oy)], color=color, sw="normal")
    d.arrow([(ox, oy), (ox, y1 - 20)], color=color, sw="normal")
    if xlabel:
        d.text(xlabel, (ox + x1) / 2, oy + 48, size="body")
    if ylabel:
        d.text(ylabel, ox - 62, (oy + y1) / 2, rotation=-90, size="body")
    for x, t in xticks:
        d.text(t, x, oy + 18, size="small", color="neutral")
    for y, t in yticks:
        d.text(t, ox - 30, y, size="small", color="neutral")


def table(d, x, y, col_widths, headers, rows, row_h=52, header_h=36, cell=None, zebra=True):
    """Simple table. rows: list of lists of markup strings; cell(d, ri, ci, box) may draw custom content
    (return True to skip the default text). Returns list of row boxes."""
    cx = x
    for w, h in zip(col_widths, headers):
        d.rect(cx, y, w, header_h, f"**{h}**", fill="primary", stroke="background", color="background", size="label")
        cx += w
    out = []
    total = sum(col_widths)
    for ri, row in enumerate(rows):
        ry = y + header_h + ri * row_h
        odd = zebra and ri % 2 == 0
        d.rect(x, ry, total, row_h, fill="secondary" if odd else "background", fill_opacity="wash" if odd else None,
               stroke="neutral", sw="thin")
        cx = x
        for ci, (w, val) in enumerate(zip(col_widths, row)):
            box = (cx, ry, w, row_h)
            if not (cell and cell(d, ri, ci, box)) and val:
                d.text(val, cx + 14, ry + row_h / 2, anchor="w", size="body")
            cx += w
        out.append((x, ry, total, row_h))
    return out
