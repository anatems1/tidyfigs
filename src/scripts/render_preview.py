#!/usr/bin/env python3
"""
render_preview.py — rasterize a .drawio file to PNG so it can be compared with the source image.

    python render_preview.py fig.drawio -o preview.png              # page-aligned, 1 px per unit
    python render_preview.py fig.drawio -o preview.png --width 1408 # resize to match source width
    python render_preview.py fig.drawio -o preview.png --engine drawio   # use draw.io desktop CLI

Engines
  kit    (default) built-in PIL renderer. Page-aligned (pixel (0,0) == page origin), so the output
         overlays exactly on the source image. Approximates draw.io: rects/rounded, ellipses, stars,
         triangles, rhombus, text with HTML bold/italic/color/wrap, images (JPEG/PNG + the SVG
         polygons/polylines/circles/paths drawio_kit emits), straight/orthogonal/curved edges,
         arrowheads, dashes, flexArrow, opacity, groups. Unknown shapes fall back to rectangles.
  drawio the real draw.io desktop app (if installed; uses xvfb-run when there is no display).
         Exact rendering but cropped to the diagram bounds — use for a final visual check, not overlay.
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import base64
import html
import io
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drawio_kit import catmull_rom, find_font_file, html_lines, render_math  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

SS = 2  # supersampling factor for anti-aliasing


# ------------------------------------------------------------------ parsing
def load_model(path):
    root = ET.parse(path).getroot()
    if root.tag == "mxGraphModel":
        return root
    diag = root.find("diagram")
    model = diag.find("mxGraphModel")
    if model is None:  # compressed diagram
        data = base64.b64decode(diag.text.strip())
        xml = urllib.parse.unquote(zlib.decompress(data, -15).decode())
        model = ET.fromstring(xml)
    return model


def parse_style(s):
    tokens, kv = [], {}
    for part in (s or "").split(";"):
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            kv[k] = v
        else:
            tokens.append(part)
    return tokens, kv


def hex2rgba(c, alpha=255):
    if not c or c == "none" or c == "default":
        return None
    c = c.strip()
    if c.startswith("#"):
        c = c[1:]
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        try:
            return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), int(alpha))
        except ValueError:
            return None
    named = {"white": "ffffff", "black": "000000", "red": "ff0000", "gray": "808080", "grey": "808080"}
    return hex2rgba("#" + named[c.lower()], alpha) if c.lower() in named else None


def fnum(kv, k, d):
    try:
        return float(kv.get(k, d))
    except (TypeError, ValueError):
        return d


# ------------------------------------------------------------------ renderer
class Renderer:
    def __init__(self, model, scale=1.0):
        self.model = model
        self.k = scale * SS
        # draw.io also wraps cells in <UserObject>/<object> elements
        self.cells = []
        for o in model.find("root"):
            if o.tag == "mxCell":
                self.cells.append((o, o))
            else:
                c = o.find("mxCell")
                if c is not None:
                    c.set("id", o.get("id")); c.set("value", o.get("label", ""))
                    self.cells.append((c, o))
        self.by_id = {c.get("id"): c for c, _ in self.cells}
        self._abs = {}
        pw = fnum(model.attrib, "pageWidth", 850); ph = fnum(model.attrib, "pageHeight", 1100)
        self.W, self.H = int(math.ceil(pw * self.k)), int(math.ceil(ph * self.k))
        self.math = model.get("math") == "1"
        bg = hex2rgba(model.get("background")) or (255, 255, 255, 255)
        self.img = Image.new("RGB", (self.W, self.H), bg[:3])
        self.draw = ImageDraw.Draw(self.img, "RGBA")

    # ---- geometry
    def abs_geo(self, cid):
        if cid in self._abs:
            return self._abs[cid]
        c = self.by_id.get(cid)
        if c is None or c.find("mxGeometry") is None:
            self._abs[cid] = (0, 0, 0, 0); return self._abs[cid]
        g = c.find("mxGeometry")
        x, y = fnum(g.attrib, "x", 0), fnum(g.attrib, "y", 0)
        w, h = fnum(g.attrib, "width", 0), fnum(g.attrib, "height", 0)
        p = c.get("parent")
        if p and p not in ("0", "1") and p in self.by_id and self.by_id[p].get("vertex") == "1":
            px, py, _, _ = self.abs_geo(p)
            x, y = x + px, y + py
        self._abs[cid] = (x, y, w, h)
        return self._abs[cid]

    def K(self, v):
        return v * self.k

    # ---- helpers
    def color(self, kv, key, default=None, opacity_keys=("opacity",)):
        a = 255
        for ok in opacity_keys:
            if ok in kv:
                a *= fnum(kv, ok, 100) / 100
        return hex2rgba(kv.get(key, default), a)

    def stroke_w(self, kv):
        return max(1, int(round(fnum(kv, "strokeWidth", 1) * self.k)))

    def dashed_line(self, pts, fill, width, pattern):
        on, off = [float(p) * self.k * max(1, width / self.k) ** 0.5 for p in (pattern.split() + ["4"])[:2]]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            L = math.dist((x1, y1), (x2, y2))
            if L == 0:
                continue
            ux, uy = (x2 - x1) / L, (y2 - y1) / L
            t, draw_on = 0.0, True
            while t < L:
                seg = min(on if draw_on else off, L - t)
                if draw_on:
                    self.draw.line([(x1 + ux * t, y1 + uy * t), (x1 + ux * (t + seg), y1 + uy * (t + seg))],
                                   fill=fill, width=width)
                t += seg; draw_on = not draw_on

    def polyline(self, pts, fill, width, dashed=False, pattern="3 3"):
        if fill is None or len(pts) < 2:
            return
        if dashed:
            self.dashed_line(pts, fill, width, pattern)
        else:
            self.draw.line(pts, fill=fill, width=width, joint="curve")

    # ---- shapes
    def shape_poly(self, kind, x, y, w, h, kv):
        if kind == "star":
            cx, cy, R = x + w / 2, y + h / 2, min(w, h) / 2
            r = R * 0.45
            return [(cx + (R if i % 2 == 0 else r) * math.sin(math.pi * i / 5),
                     cy + 0.06 * h - (R if i % 2 == 0 else r) * math.cos(math.pi * i / 5)) for i in range(10)]
        if kind == "triangle":
            d = kv.get("direction", "east")
            return {"north": [(x, y + h), (x + w / 2, y), (x + w, y + h)],
                    "south": [(x, y), (x + w, y), (x + w / 2, y + h)],
                    "west": [(x + w, y), (x + w, y + h), (x, y + h / 2)]}.get(d, [(x, y), (x + w, y + h / 2), (x, y + h)])
        if kind == "rhombus":
            return [(x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h), (x, y + h / 2)]
        if kind == "hexagon":
            s = w * fnum(kv, "size", 0.25)
            return [(x + s, y), (x + w - s, y), (x + w, y + h / 2), (x + w - s, y + h), (x + s, y + h), (x, y + h / 2)]
        if kind == "parallelogram":
            s = w * fnum(kv, "size", 0.2)
            return [(x + s, y), (x + w, y), (x + w - s, y + h), (x, y + h)]
        if kind == "trapezoid":
            s = w * fnum(kv, "size", 0.2)
            return [(x + s, y), (x + w - s, y), (x + w, y + h), (x, y + h)]
        return None

    def draw_vertex(self, c):
        tokens, kv = parse_style(c.get("style"))
        x, y, w, h = self.abs_geo(c.get("id"))
        X, Y, Wd, Ht = self.K(x), self.K(y), self.K(w), self.K(h)
        shape = kv.get("shape") or next((t for t in tokens if t in ("ellipse", "rhombus", "triangle", "text",
                                                                    "image", "swimlane", "line")), "rect")
        if "mxgraph.basic.star" in (kv.get("shape") or ""):
            shape = "star"
        if "group" in tokens:
            return
        fill = self.color(kv, "fillColor", None, ("opacity", "fillOpacity"))
        stroke = self.color(kv, "strokeColor", "#000000", ("opacity", "strokeOpacity"))
        if "text" in tokens:
            fill = self.color(kv, "fillColor", None, ("opacity", "fillOpacity")) if kv.get("fillColor") not in (None, "none") else None
            stroke = None if kv.get("strokeColor") in (None, "none") else stroke
        sw = self.stroke_w(kv)
        dashed = kv.get("dashed") == "1"
        if shape == "image":
            self.draw_image(kv, X, Y, Wd, Ht)
        elif shape in ("ellipse", "doubleEllipse") or "ellipse" in tokens:
            self.draw.ellipse([X, Y, X + Wd, Y + Ht], fill=fill, outline=None)
            if stroke and dashed:
                ring = [(X + Wd / 2 + Wd / 2 * math.cos(t / 72 * math.tau), Y + Ht / 2 + Ht / 2 * math.sin(t / 72 * math.tau)) for t in range(73)]
                self.polyline(ring, stroke, sw, True, kv.get("dashPattern", "3 3"))
            elif stroke:
                self.draw.ellipse([X, Y, X + Wd, Y + Ht], outline=stroke, width=sw)
        elif shape in ("star", "triangle", "rhombus", "hexagon", "parallelogram", "trapezoid") or \
                self.shape_poly(shape, X, Y, Wd, Ht, kv):
            pts = self.shape_poly(shape, X, Y, Wd, Ht, kv) or [(X, Y), (X + Wd, Y), (X + Wd, Y + Ht), (X, Y + Ht)]
            self.draw.polygon(pts, fill=fill)
            if stroke:
                self.polyline(pts + pts[:1], stroke, sw, dashed, kv.get("dashPattern", "3 3"))
        elif shape == "line":
            self.draw.line([(X, Y + Ht / 2), (X + Wd, Y + Ht / 2)], fill=stroke, width=sw)
        elif "text" not in tokens or fill or stroke:
            r = 0
            if kv.get("rounded") == "1":
                r = (fnum(kv, "arcSize", 16) / 2 * self.k if kv.get("absoluteArcSize") == "1"
                     else min(Wd, Ht) * fnum(kv, "arcSize", 15) / 100)
                r = max(0, min(r, (min(Wd, Ht) - 4) / 2))
            box = [X, Y, X + Wd, Y + Ht]
            g2 = self.color(kv, "gradientColor", None, ("opacity", "fillOpacity"))
            if fill and g2:   # gradient fill (south/north/east/west) drawn as strips inside a rounded mask
                horiz = kv.get("gradientDirection", "south") in ("east", "west")
                flip = kv.get("gradientDirection", "south") in ("north", "west")
                n = int(Wd if horiz else Ht) or 1
                layer = Image.new("RGBA", (max(1, int(Wd)), max(1, int(Ht))), (0, 0, 0, 0))
                ld = ImageDraw.Draw(layer)
                for i in range(n):
                    t = i / max(1, n - 1)
                    t = 1 - t if flip else t
                    col = tuple(int(fill[j] + (g2[j] - fill[j]) * t) for j in range(4))
                    ld.line([(i, 0), (i, Ht)] if horiz else [(0, i), (Wd, i)], fill=col)
                mask = Image.new("L", layer.size, 0)
                ImageDraw.Draw(mask).rounded_rectangle([0, 0, layer.width - 1, layer.height - 1], radius=r, fill=255)
                alpha = Image.composite(layer.split()[3], Image.new("L", layer.size, 0), mask)
                layer.putalpha(alpha)
                self.img.paste(layer, (int(X), int(Y)), layer)
            elif fill:
                self.draw.rounded_rectangle(box, radius=r, fill=fill)
            if stroke and kv.get("strokeColor") != "none":
                if dashed:
                    self.polyline([(X, Y), (X + Wd, Y), (X + Wd, Y + Ht), (X, Y + Ht), (X, Y)], stroke, sw, True,
                                  kv.get("dashPattern", "3 3"))
                else:
                    self.draw.rounded_rectangle(box, radius=r, outline=stroke, width=sw)
        self.draw_label(c.get("value") or "", kv, tokens, X, Y, Wd, Ht)

    # ---- images (raster + the SVG subset drawio_kit emits)
    def draw_image(self, kv, X, Y, Wd, Ht):
        src = kv.get("image", "")
        m = re.match(r"data:image/([\w+.-]+)[,;](?:base64,)?(.*)", src, re.S)
        if not m or Wd < 1 or Ht < 1:
            return
        kind, data = m.group(1), m.group(2)
        try:
            raw = base64.b64decode(data + "=" * (-len(data) % 4))
        except Exception:
            return
        if kind.startswith("svg"):
            self.draw_svg(raw.decode("utf-8", "replace"), X, Y, Wd, Ht, kv)
        else:
            try:
                im = Image.open(io.BytesIO(raw)).convert("RGBA").resize((max(1, int(Wd)), max(1, int(Ht))), Image.LANCZOS)
                self.img.paste(im, (int(X), int(Y)), im)
            except Exception:
                return
        if kv.get("imageBorder"):
            self.draw.rectangle([X, Y, X + Wd, Y + Ht], outline=hex2rgba(kv["imageBorder"]), width=max(1, int(self.k)))

    def draw_svg(self, svg, X, Y, Wd, Ht, kv):
        try:
            root = ET.fromstring(svg)
        except ET.ParseError:
            return
        vb = [float(v) for v in re.split(r"[ ,]+", root.get("viewBox", "").strip())] if root.get("viewBox") else \
            [0, 0, float(re.sub(r"[^\d.]", "", root.get("width", "100"))), float(re.sub(r"[^\d.]", "", root.get("height", "100")))]
        sx, sy = Wd / vb[2], Ht / vb[3]
        op = fnum(kv, "opacity", 100) / 100

        def T(px, py):
            return (X + (px - vb[0]) * sx, Y + (py - vb[1]) * sy)
        for el in root.iter():
            tag = el.tag.split("}")[-1]
            if tag not in ("polygon", "polyline", "circle", "path", "rect", "ellipse", "line"):
                continue
            fill = hex2rgba(el.get("fill", "#000000" if tag != "polyline" else "none"),
                            255 * float(el.get("fill-opacity", 1)) * float(el.get("opacity", 1)) * op)
            stroke = hex2rgba(el.get("stroke", "none"), 255 * float(el.get("stroke-opacity", 1)) * float(el.get("opacity", 1)) * op)
            sw = max(1, int(round(float(el.get("stroke-width", 1)) * sx)))
            dash = el.get("stroke-dasharray")
            polys = []
            if tag in ("polygon", "polyline"):
                nums = [float(v) for v in re.split(r"[ ,]+", el.get("points", "").strip()) if v]
                polys = [([T(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)], tag == "polygon")]
            elif tag == "line":
                polys = [([T(float(el.get("x1", 0)), float(el.get("y1", 0))), T(float(el.get("x2", 0)), float(el.get("y2", 0)))], False)]
            elif tag == "rect":
                x0, y0 = float(el.get("x", 0)), float(el.get("y", 0)); w0, h0 = float(el.get("width", 0)), float(el.get("height", 0))
                polys = [([T(x0, y0), T(x0 + w0, y0), T(x0 + w0, y0 + h0), T(x0, y0 + h0)], True)]
            elif tag in ("circle", "ellipse"):
                cx, cy = float(el.get("cx", 0)), float(el.get("cy", 0))
                rx = float(el.get("r", el.get("rx", 0))); ry = float(el.get("r", el.get("ry", 0)))
                polys = [([T(cx + rx * math.cos(t / 24 * math.tau), cy + ry * math.sin(t / 24 * math.tau)) for t in range(24)], True)]
            elif tag == "path":
                polys = [(list(map(lambda p: T(*p), sp)), closed) for sp, closed in parse_path(el.get("d", ""))]
            for pts, closed in polys:
                if len(pts) < 2:
                    continue
                if closed and fill:
                    self.draw.polygon(pts, fill=fill)
                if stroke:
                    self.polyline(pts + (pts[:1] if closed else []), stroke, sw, bool(dash), (dash or "3 3").replace(",", " "))

    # ---- labels
    def draw_label(self, value, kv, tokens, X, Y, Wd, Ht):
        if not value:
            return
        if self.math:   # whole-label LaTeX ($$...$$ or \(...\)) -> mathtext image
            plain = html.unescape(re.sub(r"<[^>]+>", "", value)).strip()
            m = re.fullmatch(r"\$\$(.+)\$\$|\\\((.+)\\\)", plain, re.S)
            if m:
                col = kv.get("fontColor", "#000000")
                im = render_math(m.group(1) or m.group(2), fnum(kv, "fontSize", 11) * self.k, col if col.startswith("#") else "#000000")
                if im is not None:
                    al = kv.get("align", "center")
                    px = {"left": X, "right": X + Wd - im.width}.get(al, X + (Wd - im.width) / 2)
                    self.img.paste(im, (int(px), int(Y + (Ht - im.height) / 2)), im)
                    return
        is_html = kv.get("html") == "1"
        lines = html_lines(value) if is_html else html_lines(value, raw_text=True)
        fam = kv.get("fontFamily", "Helvetica")
        size = fnum(kv, "fontSize", 11)
        fstyle = int(fnum(kv, "fontStyle", 0))
        base_color = kv.get("fontColor", "#000000")
        alpha = 255 * fnum(kv, "textOpacity", 100) / 100 * fnum(kv, "opacity", 100) / 100
        spacing = fnum(kv, "spacing", 2)
        pad = {s: (spacing + fnum(kv, "spacing" + s.capitalize(), 0)) * self.k for s in ("left", "right", "top", "bottom")}
        if kv.get("verticalLabelPosition") == "bottom":
            Y, Ht = Y + Ht, size * 2 * self.k
        avail = Wd - pad["left"] - pad["right"]
        # segment fonts
        def seg_font(sg):
            b = bool(fstyle & 1) or sg.get("bold"); i = bool(fstyle & 2) or sg.get("italic")
            sz = (sg.get("size") or size) * self.k
            path = find_font_file(fam, b, i)
            try:
                return ImageFont.truetype(path, max(1, int(round(sz)))) if path else ImageFont.load_default()
            except Exception:
                return ImageFont.load_default()
        # word wrap
        if kv.get("whiteSpace") == "wrap" and avail > 0:
            wrapped = []
            for line in lines:
                cur, cur_w = [], 0.0
                words = []
                for sg in line:
                    for tok in re.split(r"(\s+)", sg["text"]):
                        if tok:
                            words.append(dict(sg, text=tok))
                for wd in words:
                    mm = re.fullmatch(r"(.*?)\\\((.+?)\\\)(.*)", wd["text"])
                    if mm:   # token containing inline math: measure the rendered math
                        mi = render_math(mm.group(2), (wd.get("size") or size) * self.k)
                        ww = (mi.width if mi is not None else 0) + seg_font(wd).getlength(mm.group(1) + mm.group(3))
                    else:
                        ww = seg_font(wd).getlength(wd["text"])
                    if cur and cur_w + ww > avail + 1 and not wd["text"].isspace():
                        wrapped.append(cur); cur, cur_w = [], 0.0
                    if not cur and wd["text"].isspace():
                        continue
                    cur.append(wd); cur_w += ww
                wrapped.append(cur)
            lines = wrapped
        lh = size * 1.2 * self.k
        total_h = lh * len(lines)
        va = kv.get("verticalAlign", "middle")
        top = {"top": Y + pad["top"], "bottom": Y + Ht - pad["bottom"] - total_h}.get(va, Y + (Ht - total_h) / 2)
        align = kv.get("align", "center")
        rot = fnum(kv, "rotation", 0)
        layer, ox, oy = (None, 0, 0)
        if rot:
            layer = Image.new("RGBA", (int(Wd) + 4, int(Ht) + 4), (0, 0, 0, 0))
            ldraw = ImageDraw.Draw(layer)
            ox, oy = X, Y
        else:
            ldraw = self.draw
        for i, line in enumerate(lines):
            # expand emoji into their own segments (no emoji font is assumed: drawn as placeholders)
            line = [dict(sg, text=run, emoji=e) for sg in line for e, run in split_emoji(sg["text"])]
            # inline LaTeX \( ... \) -> math segments rendered with mathtext
            ml = []
            for sg in line:
                parts = re.split(r"\\\((.+?)\\\)", sg["text"]) if not sg.get("emoji") else [sg["text"]]
                for pi, p in enumerate(parts):
                    if p:
                        ml.append(dict(sg, text=p, math=(pi % 2 == 1)))
            line = ml
            fonts = [seg_font(sg) for sg in line]
            mims = [render_math(sg["text"], (sg.get("size") or size) * self.k, sg.get("color") or (base_color if base_color.startswith("#") else "#000000"))
                    if sg.get("math") else None for sg in line]
            widths = [mi.width if mi is not None else f.size * 1.05 if sg.get("emoji") else f.getlength(sg["text"])
                      for f, sg, mi in zip(fonts, line, mims)]
            lw = sum(widths)
            x0 = {"left": X + pad["left"], "right": X + Wd - pad["right"] - lw}.get(align, X + (Wd - lw) / 2)
            yb = top + i * lh + lh / 2
            cx = x0
            for f, sg, wdt, mi in zip(fonts, line, widths, mims):
                col = hex2rgba(sg.get("color") or base_color, alpha) or (0, 0, 0, int(alpha))
                if mi is not None:
                    tgt = layer if rot and layer is not None else self.img
                    tgt.paste(mi, (int(cx - ox), int(yb - oy - mi.height / 2)), mi)
                    cx += wdt
                    continue
                if sg.get("emoji"):   # icon placeholder: soft rounded square the size of the glyph
                    r = f.size * 0.45
                    ldraw.rounded_rectangle([cx - ox + wdt / 2 - r, yb - oy - r, cx - ox + wdt / 2 + r, yb - oy + r],
                                            radius=r * 0.35, fill=(150, 160, 175, int(alpha * 0.45)),
                                            outline=(90, 100, 115, int(alpha * 0.8)), width=max(1, int(self.k)))
                    cx += wdt
                    continue
                ldraw.text((cx - ox, yb - oy), sg["text"], font=f, fill=col, anchor="lm")
                if (fstyle & 4) or sg.get("underline"):
                    ldraw.line([(cx - ox, yb - oy + f.size * 0.55), (cx - ox + wdt, yb - oy + f.size * 0.55)], fill=col, width=max(1, int(self.k)))
                cx += wdt
        if rot and layer is not None:
            layer = layer.rotate(-rot, expand=True, resample=Image.BICUBIC)
            cxp, cyp = X + Wd / 2, Y + Ht / 2
            self.img.paste(layer, (int(cxp - layer.width / 2), int(cyp - layer.height / 2)), layer)

    # ---- edges
    def endpoint(self, cid, toward, frac=None):
        x, y, w, h = self.abs_geo(cid)
        if frac is not None:
            return (x + w * frac[0], y + h * frac[1])
        cx, cy = x + w / 2, y + h / 2
        dx, dy = toward[0] - cx, toward[1] - cy
        if dx == 0 and dy == 0:
            return (cx, cy)
        tokens, kv = parse_style(self.by_id[cid].get("style"))
        if "ellipse" in tokens or "star" in (kv.get("shape") or ""):
            a = math.atan2(dy, dx)
            return (cx + w / 2 * math.cos(a), cy + h / 2 * math.sin(a))
        sx = (w / 2) / abs(dx) if dx else float("inf")
        sy = (h / 2) / abs(dy) if dy else float("inf")
        s = min(sx, sy)
        return (cx + dx * s, cy + dy * s)

    def draw_edge(self, c):
        tokens, kv = parse_style(c.get("style"))
        g = c.find("mxGeometry")
        if g is None:
            return
        sp = g.find("mxPoint[@as='sourcePoint']"); tp = g.find("mxPoint[@as='targetPoint']")
        arr = g.find("Array[@as='points']")
        way = [(fnum(p.attrib, "x", 0), fnum(p.attrib, "y", 0)) for p in arr] if arr is not None else []
        src, tgt = c.get("source"), c.get("target")

        def frac(prefix):
            return (fnum(kv, prefix + "X", 0.5), fnum(kv, prefix + "Y", 0.5)) if prefix + "X" in kv else None
        if src and src in self.by_id:
            sx, sy, sw_, sh_ = self.abs_geo(src)
            ref = way[0] if way else (self.abs_geo(tgt)[0] + self.abs_geo(tgt)[2] / 2, self.abs_geo(tgt)[1] + self.abs_geo(tgt)[3] / 2) if tgt in self.by_id else \
                ((fnum(tp.attrib, "x", 0), fnum(tp.attrib, "y", 0)) if tp is not None else (sx, sy))
            p0 = self.endpoint(src, ref, frac("exit"))
        else:
            p0 = (fnum(sp.attrib, "x", 0), fnum(sp.attrib, "y", 0)) if sp is not None else (0, 0)
        if tgt and tgt in self.by_id:
            ref = way[-1] if way else p0
            p1 = self.endpoint(tgt, ref, frac("entry"))
        else:
            p1 = (fnum(tp.attrib, "x", 0), fnum(tp.attrib, "y", 0)) if tp is not None else p0
        pts = [p0] + way + [p1]
        style = kv.get("edgeStyle", "")
        if kv.get("curved") == "1" and len(pts) > 2:
            pts = drawio_curve(pts)
        elif "orthogonal" in style or "elbow" in style:
            pts = orthogonalize(pts, kv)
        P = [(self.K(x), self.K(y)) for x, y in pts]
        stroke = self.color(kv, "strokeColor", "#000000")
        sw = self.stroke_w(kv)
        if kv.get("shape") == "flexArrow":
            self.draw_flex(P, kv)
            return
        end, start = kv.get("endArrow", "classic"), kv.get("startArrow", "none")
        P2 = list(P)
        if end not in ("none", "") and len(P2) >= 2:
            P2[-1] = self.arrowhead(P2[-2], P2[-1], end, kv.get("endFill", "1") != "0", fnum(kv, "endSize", 6), stroke, sw)
        if start not in ("none", "") and len(P2) >= 2:
            P2[0] = self.arrowhead(P2[1], P2[0], start, kv.get("startFill", "1") != "0", fnum(kv, "startSize", 6), stroke, sw)
        self.polyline(P2, stroke, sw, kv.get("dashed") == "1", kv.get("dashPattern", "3 3"))
        if c.get("value"):
            mid = P[len(P) // 2] if len(P) > 2 else ((P[0][0] + P[-1][0]) / 2, (P[0][1] + P[-1][1]) / 2)
            w = 200 * self.k
            self.draw_label(c.get("value"), dict(kv, align="center", verticalAlign="middle"), tokens,
                            mid[0] - w / 2, mid[1] - 10 * self.k, w, 20 * self.k)

    def arrowhead(self, a, b, kind, filled, size, color, sw):
        L = math.dist(a, b)
        if L == 0 or color is None:
            return b
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        ln = (size * 1.5) * self.k + sw * 0.5
        hw = (size * 0.6) * self.k + sw * 0.5
        base = (b[0] - ux * ln, b[1] - uy * ln)
        left = (base[0] - uy * hw, base[1] + ux * hw); right = (base[0] + uy * hw, base[1] - ux * hw)
        if kind == "oval":
            r = hw
            self.draw.ellipse([b[0] - r, b[1] - r, b[0] + r, b[1] + r], fill=color if filled else None, outline=color)
            return (b[0] - ux * r, b[1] - uy * r)
        if kind == "diamond":
            mid = (b[0] - ux * ln / 2, b[1] - uy * ln / 2)
            pts = [b, (mid[0] - uy * hw, mid[1] + ux * hw), base, (mid[0] + uy * hw, mid[1] - ux * hw)]
        elif kind == "classic":
            notch = (b[0] - ux * ln * 0.7, b[1] - uy * ln * 0.7)
            pts = [b, left, notch, right]; base = notch
        elif kind in ("open", "dash"):
            self.draw.line([left, b, right], fill=color, width=sw)
            return b
        else:
            pts = [b, left, right]
        self.draw.polygon(pts, fill=color if filled else None, outline=color)
        return base

    def draw_flex(self, P, kv):
        fill = self.color(kv, "fillColor", "#ffffff"); stroke = self.color(kv, "strokeColor", "#000000")
        width = fnum(kv, "width", 10) * self.k
        ew = fnum(kv, "endWidth", 20) * self.k
        es = fnum(kv, "endSize", 7) * self.k * 2
        if len(P) < 2:
            return
        b, a = P[-1], P[-2]
        L = math.dist(a, b) or 1
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        base = (b[0] - ux * es, b[1] - uy * es)
        body = P[:-1] + [base]
        self.draw.line(body, fill=fill, width=int(width), joint="curve")
        hw = (width + ew) / 2
        self.draw.polygon([b, (base[0] - uy * hw, base[1] + ux * hw), (base[0] + uy * hw, base[1] - ux * hw)], fill=fill, outline=stroke)

    # ---- main
    def render(self):
        for c, _ in self.cells:
            if c.get("vertex") == "1":
                self.draw_vertex(c)
            elif c.get("edge") == "1":
                self.draw_edge(c)
        return self.img.resize((self.W // SS, self.H // SS), Image.LANCZOS)


def drawio_curve(pts, n=14):
    """draw.io 'curved=1': waypoints act as quadratic CONTROL points; the curve passes through the
    midpoints between consecutive waypoints (and the two end points), not through the waypoints."""
    p0, way, p1 = pts[0], pts[1:-1], pts[-1]
    if not way:
        return pts
    anchors = [p0] + [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(way, way[1:])] + [p1]
    out = [p0]
    for i, c in enumerate(way):
        a, b = anchors[i], anchors[i + 1]
        for k in range(1, n + 1):
            t = k / n
            out.append(((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0],
                        (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]))
    return out


def _is_emoji(ch):
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF or 0x1F900 <= o


def split_emoji(text):
    """Split into (is_emoji, run) pieces; variation selectors / ZWJ are dropped."""
    out = []
    for ch in text:
        if ch in "\ufe0f\u200d":
            continue
        e = _is_emoji(ch)
        if out and out[-1][0] == e and not e:
            out[-1] = (e, out[-1][1] + ch)
        else:
            out.append((e, ch))
    return out


def orthogonalize(pts, kv):
    """Approximate draw.io orthogonal routing: axis-aligned segments honoring exit/entry sides."""
    def side_dir(prefix):
        if prefix + "X" not in kv:
            return None
        fx, fy = fnum(kv, prefix + "X", 0.5), fnum(kv, prefix + "Y", 0.5)
        return "h" if fx in (0.0, 1.0) and 0 < fy < 1 else "v" if fy in (0.0, 1.0) else None
    p0, p1 = pts[0], pts[-1]
    if len(pts) == 2:
        d0 = side_dir("exit") or ("h" if abs(p1[0] - p0[0]) >= abs(p1[1] - p0[1]) else "v")
        d1 = side_dir("entry") or d0
        if p0[0] == p1[0] or p0[1] == p1[1]:
            return pts
        if d0 == "h" and d1 == "h":
            mx = (p0[0] + p1[0]) / 2
            return [p0, (mx, p0[1]), (mx, p1[1]), p1]
        if d0 == "v" and d1 == "v":
            my = (p0[1] + p1[1]) / 2
            return [p0, (p0[0], my), (p1[0], my), p1]
        return [p0, (p1[0], p0[1]), p1] if d0 == "h" else [p0, (p0[0], p1[1]), p1]
    out = [p0]
    horiz = (side_dir("exit") or "h") == "h"
    for p in pts[1:]:
        q = out[-1]
        if q[0] != p[0] and q[1] != p[1]:
            out.append((p[0], q[1]) if horiz else (q[0], p[1]))
        out.append(p)
        horiz = not horiz
    return out


def parse_path(d):
    """Minimal SVG path parser (M L H V C Q Z, abs + rel) -> list of (points, closed)."""
    toks = re.findall(r"[MLHVCQZmlhvcqz]|-?\d*\.?\d+(?:e-?\d+)?", d)
    paths, cur, pos, start, i, cmd = [], [], (0.0, 0.0), (0.0, 0.0), 0, None

    def num():
        nonlocal i
        v = float(toks[i]); i += 1; return v
    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]):
            cmd = toks[i]; i += 1
            if cmd in "Zz":
                if cur: paths.append((cur, True)); cur = []
                pos = start; continue
        rel = cmd.islower()
        C = cmd.upper()
        ox, oy = pos if rel else (0, 0)
        if C == "M":
            if cur: paths.append((cur, False))
            pos = (ox + num(), oy + num()); start = pos; cur = [pos]; cmd = "l" if rel else "L"
        elif C == "L":
            pos = (ox + num(), oy + num()); cur.append(pos)
        elif C == "H":
            pos = ((pos[0] if rel else 0) + num(), pos[1]); cur.append(pos)
        elif C == "V":
            pos = (pos[0], (pos[1] if rel else 0) + num()); cur.append(pos)
        elif C in "CQ":
            n = 3 if C == "C" else 2
            ctrl = [(ox + num(), oy + num()) for _ in range(n)]
            p0 = pos
            for k in range(1, 13):
                t = k / 12
                if C == "C":
                    p = tuple((1 - t) ** 3 * p0[j] + 3 * (1 - t) ** 2 * t * ctrl[0][j] + 3 * (1 - t) * t * t * ctrl[1][j] + t ** 3 * ctrl[2][j] for j in (0, 1))
                else:
                    p = tuple((1 - t) ** 2 * p0[j] + 2 * (1 - t) * t * ctrl[0][j] + t * t * ctrl[1][j] for j in (0, 1))
                cur.append(p)
            pos = ctrl[-1]
        else:
            i += 1
    if cur:
        paths.append((cur, False))
    return paths


def render_kit(path, out, scale=1.0, width=None, dpi=None):
    model = load_model(path)
    if dpi and (scale == 1.0 or scale is None):
        scale = dpi / 72.0
    img = Renderer(model, scale).render()
    if width and img.width != width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    import time
    for attempt in range(5):
        try:
            save_kw = {"dpi": (dpi, dpi)} if dpi else {}
            img.save(out, **save_kw)
            break
        except OSError:
            if attempt == 4:
                raise
            time.sleep(0.2)
    return out


def render_drawio_cli(path, out, scale=1.0):
    exe = shutil.which("drawio") or shutil.which("draw.io")
    if not exe and sys.platform.startswith("win"):
        cand = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "draw.io", "draw.io.exe")
        if os.path.exists(cand):
            exe = cand
    if not exe:
        raise SystemExit("draw.io CLI not found (install draw.io desktop) — use --engine kit")
    cmd = [exe, "--export", "--format", "png", "--scale", str(scale), "--output", out, path, "--no-sandbox"]
    if not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
        cmd = ["xvfb-run", "-a"] + cmd
    subprocess.run(cmd, check=True, capture_output=True, timeout=180)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("drawio")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--scale", type=float, default=1.0, help="output px per draw.io unit")
    ap.add_argument("--dpi", type=int, default=None, help="output DPI (e.g. 300 for print-ready PNG exports)")
    ap.add_argument("--width", type=int, default=None, help="resize output to this width (match source)")
    ap.add_argument("--engine", choices=["kit", "drawio"], default="kit")
    a = ap.parse_args()
    out = a.out or os.path.splitext(a.drawio)[0] + ".preview.png"
    if a.engine == "drawio":
        scale = (a.dpi / 72.0) if (a.dpi and a.scale == 1.0) else a.scale
        render_drawio_cli(a.drawio, out, scale)
    else:
        render_kit(a.drawio, out, a.scale, a.width, a.dpi)
    print("wrote", out)


if __name__ == "__main__":
    main()
