#!/usr/bin/env python3
r"""
drawio_kit — build *editable* draw.io (.drawio) diagrams that replicate a source image.

Design rules baked into this library
  * Coordinates are given in SOURCE-IMAGE pixels (measure them on the inspection grid).
    `scale` multiplies geometry, font sizes and page size at save time.
  * Colors, fonts, font sizes, stroke widths and opacities are referenced by THEME ROLE
    ("primary", "heading", "thick", "tint" ...). Raw hex/numbers still work but are reported
    as off-theme so lint can flag them.
  * Everything that draw.io can represent natively is emitted natively (boxes, text, edges,
    ellipses, stars, groups). Free-form geometry (polygons, blobs, meshes) becomes an embedded
    SVG image; photos are cropped from the source and embedded as JPEG/PNG.

Minimal example
    import sys; sys.path.insert(0, "<skill>/scripts")
    from drawio_kit import Diagram
    d = Diagram.from_source("images/fig.png", theme="theme.yaml")
    d.rect(40, 40, 200, 60, "**Encoder**", fill="primary", color="background", size="heading", rounded=True)
    d.text("Bidirectional context.", 140, 130, size="body", bold=True)
    d.edge([(140, 100), (140, 120)], arrow="end")
    d.save("images/fig.drawio")

Text markup (used by every `label`/`text` argument unless raw=True):
    **bold**   *italic*   __underline__   {role|colored text}   {#ff0000|hex color}   \n = line break
    \* = literal asterisk
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import base64
import contextlib
import html
import io
import json
import math
import os
import random
import re
import sys
import urllib.parse
from html.parser import HTMLParser
from xml.sax.saxutils import quoteattr

__all__ = ["Theme", "Diagram", "html_lines", "measure_line", "find_font_file", "catmull_rom", "render_math", "measure_math"]

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
DEFAULT_THEME_PATH = os.path.join(SKILL_DIR, "assets", "theme.yaml")

# --------------------------------------------------------------------------------------
# Theme
# --------------------------------------------------------------------------------------
_BUILTIN_THEME = {
    "colors": {"primary": "#19355d", "secondary": "#4276b0", "neutral": "#a4a4a4",
               "text": "#000000", "background": "#ffffff"},
    "fonts": {"sans": {"family": "Helvetica"}, "serif": {"family": "Times New Roman"},
              "mono": {"family": "Courier New"}},
    "default_font": "sans",
    "sizes": {"title": 28, "heading": 20, "subheading": 16, "body": 14, "label": 12,
              "small": 10, "caption": 18},
    "line_height": 1.2,
    "strokes": {"hairline": 0.75, "thin": 1, "normal": 1.5, "thick": 2.5, "heavy": 4},
    "opacity": {"tint": 25, "soft": 45, "faded": 35},
    "shape": {"corner_radius": 8, "shadow": False},
    "spacing": {"padding": 10, "gap": 12},
}


def _deep_merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _norm_hex(c):
    c = c.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", c):
        c = "#" + "".join(ch * 2 for ch in c[1:])
    return c


class Theme:
    """Role-based theme loaded from YAML / TOML / JSON (merged over built-in defaults)."""

    def __init__(self, data=None, path=None):
        self.data = _deep_merge(_BUILTIN_THEME, data or {})
        self.path = path
        self.colors = {k: _norm_hex(v) for k, v in self.data["colors"].items()}
        self.fonts = self.data["fonts"]
        self.sizes = self.data["sizes"]
        self.strokes = self.data["strokes"]
        self.opacities = self.data["opacity"]
        self.line_height = float(self.data.get("line_height", 1.2))
        self.off_theme = set()   # raw values used that are not part of the theme

    # ---- loading -------------------------------------------------------------------
    @classmethod
    def load(cls, path=None, overrides=None):
        if isinstance(path, Theme):
            return path
        if isinstance(path, dict):
            return cls(_deep_merge(path, overrides or {}))
        path = path or (DEFAULT_THEME_PATH if os.path.exists(DEFAULT_THEME_PATH) else None)
        data = {}
        if path:
            ext = os.path.splitext(path)[1].lower()
            with open(path, "rb") as fh:
                raw = fh.read()
            if ext in (".yaml", ".yml"):
                try:
                    import yaml
                except ImportError as e:  # pragma: no cover
                    raise SystemExit("PyYAML not installed: pip install pyyaml, or use a .toml/.json theme") from e
                data = yaml.safe_load(raw) or {}
            elif ext == ".toml":
                try:
                    import tomllib
                except ImportError:  # Python < 3.11
                    import tomli as tomllib  # type: ignore
                data = tomllib.loads(raw.decode())
            elif ext == ".json":
                data = json.loads(raw)
            else:
                raise ValueError(f"Unsupported theme format: {path}")
        return cls(_deep_merge(data, overrides or {}), path)

    def to_dict(self):
        return self.data

    # ---- resolvers -----------------------------------------------------------------
    def color(self, c):
        if c is None or c == "none":
            return "none"
        if c in self.colors:
            return self.colors[c]
        if isinstance(c, str) and c.startswith("#"):
            c = _norm_hex(c)
            if c not in self.colors.values():
                self.off_theme.add(f"color {c}")
            return c
        raise KeyError(f"Unknown color role '{c}'. Roles: {sorted(self.colors)}")

    def size(self, s):
        if isinstance(s, str):
            if s not in self.sizes:
                raise KeyError(f"Unknown size role '{s}'. Roles: {sorted(self.sizes)}")
            return float(self.sizes[s])
        if float(s) not in [float(v) for v in self.sizes.values()]:
            self.off_theme.add(f"font size {s}")
        return float(s)

    def stroke(self, s):
        if isinstance(s, str):
            return float(self.strokes[s])
        return float(s)

    def opacity(self, o):
        if o is None:
            return None
        if isinstance(o, str):
            return int(self.opacities[o])
        return int(o)

    def font_key(self, f=None):
        f = f or self.data.get("default_font", "sans")
        if f not in self.fonts:
            self.off_theme.add(f"font {f}")
            return None
        return f

    def font_family(self, f=None):
        k = self.font_key(f)
        return self.fonts[k]["family"] if k else f

    def font_source(self, f=None):
        k = self.font_key(f)
        if k and self.fonts[k].get("google"):
            fam = self.fonts[k]["family"].replace(" ", "+")
            return urllib.parse.quote(f"https://fonts.googleapis.com/css?family={fam}", safe="")
        return None


# --------------------------------------------------------------------------------------
# Fonts + text measurement (PIL), shared with render_preview.py and lint_drawio.py
# --------------------------------------------------------------------------------------
_FONT_DIRS = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
              os.path.expanduser("~/.local/share/fonts"), "/Library/Fonts", "/System/Library/Fonts",
              os.path.expanduser("~/Library/Fonts"), "C:/Windows/Fonts"]
_FONT_INDEX = None
_FONT_ALIASES = {  # family keyword -> preferred file stems (metric-compatible first)
    "sans": ["LiberationSans", "Arial", "Helvetica", "arial", "DejaVuSans"],
    "serif": ["LiberationSerif", "TimesNewRoman", "Times New Roman", "times", "DejaVuSerif"],
    "mono": ["LiberationMono", "CourierNew", "cour", "DejaVuSansMono"],
}


def _font_index():
    global _FONT_INDEX
    if _FONT_INDEX is None:
        _FONT_INDEX = {}
        for d in _FONT_DIRS:
            if os.path.isdir(d):
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith((".ttf", ".otf", ".ttc")):
                            _FONT_INDEX.setdefault(os.path.splitext(f)[0].lower(), os.path.join(root, f))
    return _FONT_INDEX


def _family_kind(family):
    f = (family or "").lower()
    if any(k in f for k in ("times", "serif", "georgia", "garamond", "cambria", "palatino")) and "sans" not in f:
        return "serif"
    if any(k in f for k in ("courier", "mono", "consol", "menlo")):
        return "mono"
    return "sans"


def find_font_file(family="Helvetica", bold=False, italic=False):
    """Best local TTF for a family (used for measuring/previewing; draw.io uses the real family)."""
    idx = _font_index()
    suffixes = (["-bolditalic", "bi", "-boldoblique", "z"] if bold and italic else
                ["-bold", "bd", "b"] if bold else ["-italic", "-oblique", "i"] if italic else
                ["-regular", "", "-book"])
    stems = [family.replace(" ", ""), family] + _FONT_ALIASES[_family_kind(family)]
    for stem in stems:
        for suf in suffixes:
            p = idx.get((stem + suf).lower())
            if p:
                return p
    for stem in _FONT_ALIASES[_family_kind(family)]:
        p = idx.get(stem.lower())
        if p:
            return p
    return next(iter(idx.values()), None)


_PIL_FONTS = {}


def _pil_font(family, size, bold=False, italic=False):
    key = (family, round(size * 4) / 4, bold, italic)
    if key not in _PIL_FONTS:
        try:
            from PIL import ImageFont
            path = find_font_file(family, bold, italic)
            _PIL_FONTS[key] = ImageFont.truetype(path, max(1, int(round(size)))) if path else None
        except Exception:
            _PIL_FONTS[key] = None
    return _PIL_FONTS[key]


INLINE_MATH = re.compile(r"\\\((.+?)\\\)")


def measure_line(segs, family="Helvetica", size=14.0):
    """Width in px of one line given segments [{'text','bold','italic','size'}].
    Inline LaTeX written as \\( ... \\) is measured as rendered math."""
    w = 0.0
    expanded = []
    for s in segs:
        parts = INLINE_MATH.split(s["text"])
        for i, p in enumerate(parts):
            if not p:
                continue
            if i % 2:
                w += measure_math(p, s.get("size") or size)[0]
            else:
                expanded.append(dict(s, text=p))
    for s in expanded:
        sz = s.get("size") or size
        f = _pil_font(family, sz, s.get("bold"), s.get("italic"))
        if f is None:
            w += len(s["text"]) * sz * (0.6 if s.get("bold") else 0.55)
        else:
            w += f.getlength(s["text"]) * (sz / max(1, int(round(sz))))
    return w


class _SegParser(HTMLParser):
    """Parse draw.io HTML labels into lines of styled segments."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = [[]]
        self.stack = [dict(bold=False, italic=False, underline=False, color=None, size=None)]

    def _push(self, **kw):
        st = dict(self.stack[-1]); st.update({k: v for k, v in kw.items() if v is not None})
        self.stack.append(st)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "br":
            self.lines.append([]); return
        if tag in ("div", "p") and self.lines[-1]:
            self.lines.append([])
        kw = {}
        if tag in ("b", "strong"): kw["bold"] = True
        if tag in ("i", "em"): kw["italic"] = True
        if tag == "u": kw["underline"] = True
        if tag == "font" and a.get("color"): kw["color"] = a["color"]
        css = a.get("style") or ""
        m = re.search(r"color:\s*(#[0-9a-fA-F]{3,6})", css)
        if m: kw["color"] = m.group(1)
        if re.search(r"font-weight:\s*(bold|[6-9]00)", css): kw["bold"] = True
        if "font-style: italic" in css or "font-style:italic" in css: kw["italic"] = True
        m = re.search(r"font-size:\s*([\d.]+)px", css)
        if m: kw["size"] = float(m.group(1))
        self._push(**kw)

    def handle_endtag(self, tag):
        if tag in ("br",):
            return
        if len(self.stack) > 1:
            self.stack.pop()
        if tag in ("div", "p"):
            self.lines.append([])

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self.lines.append([])

    def handle_data(self, data):
        if data:
            st = self.stack[-1]
            self.lines[-1].append(dict(text=data, **st))


def html_lines(value, raw_text=False):
    """draw.io label value -> list of lines, each a list of segment dicts."""
    if raw_text or value is None:
        return [[dict(text=l, bold=False, italic=False, underline=False, color=None, size=None)]
                for l in (value or "").split("\n")]
    p = _SegParser()
    p.feed(value)
    lines = p.lines
    while len(lines) > 1 and not lines[-1]:
        lines.pop()
    return lines


# --------------------------------------------------------------------------------------
# Markup -> draw.io HTML
# --------------------------------------------------------------------------------------
def markup_to_html(s, theme):
    s = s.replace("\\*", "\x00")
    s = html.escape(s, quote=False)

    def col(m):
        return f'<font color="{theme.color(m.group(1))}">{m.group(2)}</font>'
    s = re.sub(r"\{(#?[\w]+)\|(.+?)\}", col, s, flags=re.S)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s, flags=re.S)
    s = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"<i>\1</i>", s, flags=re.S)
    s = re.sub(r"__(.+?)__", r"<u>\1</u>", s, flags=re.S)
    return s.replace("\x00", "*").replace("\n", "<br>")


# --------------------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------------------
def catmull_rom(points, samples_per_seg=12, closed=False):
    """Smooth polyline through points (centripetal-ish uniform Catmull-Rom)."""
    pts = [tuple(map(float, p)) for p in points]
    if len(pts) < 3:
        return pts
    if closed:
        pts = pts[-1:] + pts + pts[:2]
    else:
        pts = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(samples_per_seg):
            t = k / samples_per_seg
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t +
                                    (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(pts[-2])
    return out


def _resample(points, n):
    """Resample a polyline to n points evenly by arc length."""
    pts = [tuple(map(float, p)) for p in points]
    d = [0.0]
    for a, b in zip(pts, pts[1:]):
        d.append(d[-1] + math.dist(a, b))
    L = d[-1] or 1.0
    out, j = [], 0
    for i in range(n):
        t = L * i / (n - 1)
        while j < len(d) - 2 and d[j + 1] < t:
            j += 1
        seg = (d[j + 1] - d[j]) or 1.0
        f = (t - d[j]) / seg
        out.append((pts[j][0] + f * (pts[j + 1][0] - pts[j][0]), pts[j][1] + f * (pts[j + 1][1] - pts[j][1])))
    return out


def point_in_polygon(px, py, poly):
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def latex_for_preview(latex):
    """MathJax-only constructs -> matplotlib mathtext equivalents (used for measuring/previewing)."""
    t = latex
    t = re.sub(r"\\(?:textcolor|color)\{[^}]*\}\{((?:[^{}]|\{[^{}]*\})*)\}", r"\1", t)
    t = re.sub(r"\\color\{[^}]*\}", "", t)
    t = t.replace(r"\text{", r"\mathrm{").replace(r"\operatorname{", r"\mathrm{")
    t = t.replace(r"\lVert", r"\Vert").replace(r"\rVert", r"\Vert").replace(r"\displaystyle", "")
    # $$...$$ is display style in MathJax: show fractions full size like MathJax does
    t = re.sub(r"\\(?<![dt])frac", r"\\dfrac", t.replace(r"\tfrac", r"\frac").replace(r"\dfrac", r"\frac"))
    return t


def render_math(latex, size_px, color="#000000"):
    """LaTeX -> transparent RGBA PIL image via matplotlib mathtext (Computer Modern), or None."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["mathtext.fontset"] = "cm"
        from matplotlib.figure import Figure
        from PIL import Image
        fig = Figure(figsize=(0.01, 0.01))
        fig.text(0, 0, "$" + latex_for_preview(latex) + "$", fontsize=size_px, color=color)
        buf = io.BytesIO()
        fig.savefig(buf, dpi=72, transparent=True, bbox_inches="tight", pad_inches=0.02, format="png")
        buf.seek(0)
        return Image.open(buf).convert("RGBA")
    except Exception:
        return None


def measure_math(latex, size_px):
    im = render_math(latex, size_px)
    if im is None:
        return len(latex) * size_px * 0.45, size_px * 1.4
    return float(im.width), float(im.height)


SHAPES = {  # friendly name -> draw.io base style
    "rect": "", "ellipse": "ellipse", "circle": "ellipse;aspect=fixed",
    "star": "shape=mxgraph.basic.star", "triangle": "triangle;direction=north",
    "triangle_down": "triangle;direction=south", "triangle_right": "triangle",
    "rhombus": "rhombus", "diamond": "rhombus", "hexagon": "shape=hexagon;perimeter=hexagonPerimeter2;size=0.25",
    "parallelogram": "shape=parallelogram;perimeter=parallelogramPerimeter;size=0.2",
    "trapezoid": "shape=trapezoid;perimeter=trapezoidPerimeter;size=0.2",
    "cylinder": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=10",
    "document": "shape=document;boundedLbl=1;size=0.25", "cloud": "ellipse;shape=cloud",
    "process": "shape=process;backgroundOutline=1;size=0.1", "note": "shape=note;size=14",
    "card": "shape=card;size=14", "actor": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top",
    "arrow_right": "shape=singleArrow;arrowWidth=0.5;arrowSize=0.3",
    "double_arrow": "shape=doubleArrow;arrowWidth=0.5;arrowSize=0.3",
    "cross": "shape=cross;size=0.25", "plus": "shape=cross;size=0.25",
    "donut": "ellipse;shape=doubleEllipse", "step": "shape=step;perimeter=stepPerimeter;size=0.2",
    "callout_box": "shape=callout;perimeter=calloutPerimeter;position2=0.5;size=12;position=0.4;base=16",
}


# --------------------------------------------------------------------------------------
# Diagram
# --------------------------------------------------------------------------------------
class Diagram:
    """Collects elements in source-pixel coordinates and serializes them as .drawio XML."""

    def __init__(self, width, height, theme=None, scale=1.0, source=None, background="background",
                 name="Page-1", grid=True, coord_scale=(1.0, 1.0), math=False):
        self.theme = Theme.load(theme)
        self.width, self.height, self.S = float(width), float(height), float(scale)
        # coord_scale: multiply every measured x/y (not font sizes) — use when coordinates were read
        # off a resized view of the source, e.g. coord_scale=(src_w / view_w, src_h / view_h)
        self.cs = tuple(map(float, coord_scale))
        self.math_enabled = math   # draw.io renders LaTeX labels ($$...$$); equation() turns it on
        self.source = source
        self._src_img = None
        self.background = background
        self.name = name
        self.grid = grid
        self.els = []
        self._ids = set()
        self._groups = []
        self._counter = 0

    @classmethod
    def from_source(cls, image_path, theme=None, scale=1.0, **kw):
        from PIL import Image
        with Image.open(image_path) as im:
            w, h = im.size
        return cls(w, h, theme=theme, scale=scale, source=image_path, **kw)

    # ---- ids / groups ---------------------------------------------------------------
    def _new_id(self, want=None):
        base = re.sub(r"[^\w\-]", "_", want) if want else None
        if base and base not in self._ids:
            self._ids.add(base); return base
        while True:
            self._counter += 1
            cand = f"{base or 'el'}_{self._counter}"
            if cand not in self._ids:
                self._ids.add(cand); return cand

    def _parent(self):
        return self._groups[-1] if self._groups else None

    @contextlib.contextmanager
    def group(self, name=None):
        """Everything created inside is grouped (moves together in draw.io). Edges stay top-level."""
        gid = self._new_id(name or "group")
        self.els.append(dict(kind="group", id=gid, parent=self._parent()))
        self._groups.append(gid)
        try:
            yield gid
        finally:
            self._groups.pop()

    def get(self, id):
        return next(e for e in self.els if e["id"] == id)

    def bbox(self, id):
        e = self.get(id)
        return e["geo"]

    # ---- style helpers --------------------------------------------------------------
    def _font_style(self, font=None, size="body", color="text", bold=False, italic=False,
                    underline=False, align="center", valign="middle", wrap=True, spacing=None):
        t = self.theme
        st = {"html": "1", "fontFamily": t.font_family(font), "fontSize": t.size(size),
              "fontColor": t.color(color), "align": align, "verticalAlign": valign,
              "whiteSpace": "wrap" if wrap else "nowrap"}
        fs = (1 if bold else 0) | (2 if italic else 0) | (4 if underline else 0)
        if fs:
            st["fontStyle"] = fs
        src = t.font_source(font)
        if src:
            st["fontSource"] = src
        if spacing is not None:
            st["spacing"] = spacing
        return st

    def _shape_style(self, fill="background", stroke="text", sw="normal", rounded=False, dashed=False,
                     dash=None, opacity=None, fill_opacity=None, stroke_opacity=None, shadow=None,
                     gradient=None, gradient_dir="south"):
        t = self.theme
        st = {"fillColor": t.color(fill), "strokeColor": t.color(stroke), "strokeWidth": t.stroke(sw)}
        if gradient:
            st.update(gradientColor=t.color(gradient), gradientDirection=gradient_dir)
        if rounded:
            r = t.data["shape"]["corner_radius"] if rounded is True else rounded
            st.update(rounded=1, absoluteArcSize=1, arcSize=round(2 * r, 1))
        else:
            st["rounded"] = 0
        if dashed:
            st.update(dashed=1, dashPattern=dash or "6 4")
        for k, v in (("opacity", opacity), ("fillOpacity", fill_opacity), ("strokeOpacity", stroke_opacity)):
            if v is not None:
                st[k] = t.opacity(v)
        if shadow if shadow is not None else t.data["shape"].get("shadow"):
            st["shadow"] = 1
        return st

    def _label(self, s, raw):
        if not s:
            return ""
        return s if raw else markup_to_html(s, self.theme)

    def _add_vertex(self, id, x, y, w, h, tokens, style, value=""):
        el = dict(kind="vertex", id=self._new_id(id), parent=self._parent(),
                  geo=[float(x), float(y), float(w), float(h)], tokens=tokens, style=style, value=value)
        self.els.append(el)
        return el["id"]

    # ---- primitives -----------------------------------------------------------------
    def rect(self, x, y, w, h, label="", *, fill="background", stroke="text", sw="normal", rounded=False,
             dashed=False, dash=None, opacity=None, fill_opacity=None, stroke_opacity=None, shadow=None,
             id=None, raw=False, extra=None, font=None, size="body", color="text", bold=False, italic=False,
             underline=False, align="center", valign="middle", wrap=True, spacing=None, shape="rect",
             gradient=None, gradient_dir="south"):
        """Box (or any SHAPES entry via shape=) with an optional centered/aligned label.
        rounded: True (theme corner_radius) or a radius in px. gradient: second color role (top->bottom)."""
        st = self._shape_style(fill, stroke, sw, rounded, dashed, dash, opacity, fill_opacity, stroke_opacity, shadow,
                               gradient, gradient_dir)
        st.update(self._font_style(font, size, color, bold, italic, underline, align, valign, wrap, spacing))
        st.update(extra or {})
        base = SHAPES.get(shape, shape)
        return self._add_vertex(id, x, y, w, h, base, st, self._label(label, raw))

    def shape(self, kind, x, y, w, h, label="", **kw):
        """Any named shape: star, triangle, rhombus, hexagon, cylinder, document, cloud, ... (see SHAPES)
        or a raw draw.io base style such as 'shape=mxgraph.aws4.lambda'."""
        return self.rect(x, y, w, h, label, shape=kind, **kw)

    def ellipse(self, x, y, w, h, label="", **kw):
        return self.rect(x, y, w, h, label, shape="ellipse", **kw)

    def circle(self, cx, cy, r, label="", **kw):
        return self.rect(cx - r, cy - r, 2 * r, 2 * r, label, shape="circle", **kw)

    def dot(self, cx, cy, r=4, fill="neutral", stroke="none", **kw):
        """Small marker (scatter point)."""
        kw.setdefault("sw", "thin")
        return self.circle(cx, cy, r, fill=fill, stroke=stroke, **kw)

    def star(self, cx, cy, size, fill="secondary", stroke="primary", **kw):
        return self.shape("star", cx - size / 2, cy - size / 2, size, size, fill=fill, stroke=stroke, **kw)

    def text(self, s, x, y, *, w=None, h=None, anchor="center", size="body", font=None, color="text",
             bold=False, italic=False, underline=False, align=None, valign="middle", wrap=False, rotation=0,
             opacity=None, id=None, raw=False, pad=4, extra=None):
        """Free text. (x, y) is the anchor point: center|n|s|e|w|ne|nw|se|sw. Auto-sizes if w/h omitted.
        bold/italic apply to the whole label; use **..** / *..* for partial styling."""
        value = self._label(s, raw)
        fam, sz = self.theme.font_family(font), self.theme.size(size)
        lines = html_lines(value)
        if bold:
            for l in lines:
                for sg in l: sg["bold"] = True
        if w is None:
            w = max((measure_line(l, fam, sz) for l in lines), default=0) + pad
        if h is None:
            h = len(lines) * sz * self.theme.line_height + 2
        ax = {"w": 0, "nw": 0, "sw": 0, "e": 1, "ne": 1, "se": 1}.get(anchor, 0.5)
        ay = {"n": 0, "nw": 0, "ne": 0, "s": 1, "sw": 1, "se": 1}.get(anchor, 0.5)
        align = align or {0: "left", 1: "right"}.get(ax, "center")
        st = self._font_style(font, size, color, bold, italic, underline, align, valign, wrap, spacing=0)
        st.update(strokeColor="none", fillColor="none")
        if rotation:
            st["rotation"] = rotation
        if opacity is not None:
            st["textOpacity"] = self.theme.opacity(opacity)
        st.update(extra or {})
        return self._add_vertex(id, x - ax * w, y - ay * h, w, h, "text", st, value)

    def icon(self, glyph, cx, cy, size=24, **kw):
        """Emoji / unicode glyph used as an icon placeholder (draw.io renders it as text)."""
        kw.setdefault("raw", True)
        return self.text(glyph, cx, cy, size=size, w=size * 1.4, h=size * 1.4, **kw)

    def equation(self, latex, x, y, *, w=None, h=None, anchor="center", size="body", color="text",
                 align=None, opacity=None, id=None, pad=8, extra=None):
        """LaTeX equation as a native draw.io math label (MathJax; editable in draw.io).
        Enables math for the diagram. Auto-sizes with matplotlib mathtext when w/h are omitted.
        Write plain LaTeX without delimiters, e.g. r"s(q,d)=\\lambda\\,\\mathrm{sim}(\\mathbf{q},\\mathbf{d})".
        To annotate individual terms, place each term as its own equation() (positions are then known)."""
        self.math_enabled = True
        sz = self.theme.size(size)
        if w is None or h is None:
            mw, mh = measure_math(latex, sz)
            w = w or mw * 1.08 + pad
            h = h or mh + pad
        ax = {"w": 0, "nw": 0, "sw": 0, "e": 1, "ne": 1, "se": 1}.get(anchor, 0.5)
        ay = {"n": 0, "nw": 0, "ne": 0, "s": 1, "sw": 1, "se": 1}.get(anchor, 0.5)
        align = align or {0: "left", 1: "right"}.get(ax, "center")
        st = self._font_style(None, size, color, align=align, valign="middle", wrap=False, spacing=0)
        st.update(strokeColor="none", fillColor="none")
        if opacity is not None:
            st["textOpacity"] = self.theme.opacity(opacity)
        st.update(extra or {})
        value = "$$" + html.escape(latex, quote=False) + "$$"
        return self._add_vertex(id or "eq", x - ax * w, y - ay * h, w, h, "text", st, value)

    # ---- edges ----------------------------------------------------------------------
    _HEADS = {"block": ("block", 1), "classic": ("classic", 1), "open": ("open", 0), "oval": ("oval", 1),
              "diamond": ("diamond", 1), "openblock": ("block", 0), "dash": ("dash", 0), "none": ("none", 0)}

    def edge(self, pts=(), src=None, tgt=None, *, color="text", sw="normal", arrow="end", head="block",
             head_size=6, dashed=False, dash=None, route="straight", exit=None, entry=None, label=None,
             label_size="label", opacity=None, id=None, extra=None):
        """Connector/line. pts lists the points draw.io cannot compute, in source px:
            [start (only if no src), *waypoints, end (only if no tgt)].
        e.g. edge([(0,0), (50,0), (50,40)]) free polyline; edge([(50,0)], src="a", tgt="b") one
        waypoint between attached shapes; edge([(10,10)], tgt="b") free start, attached end.
        route: straight | orthogonal | rounded | curved (spline through waypoints).
        exit/entry: (fx, fy) fractions on the source/target bounds, e.g. (1, 0.5) = right middle."""
        t = self.theme
        pts = [tuple(map(float, p)) for p in pts]
        st = {"html": "1", "strokeColor": t.color(color), "strokeWidth": t.stroke(sw)}
        st.update({"straight": {"edgeStyle": "none", "rounded": 0},
                   "orthogonal": {"edgeStyle": "orthogonalEdgeStyle", "rounded": 0},
                   "rounded": {"edgeStyle": "orthogonalEdgeStyle", "rounded": 1},
                   "curved": {"edgeStyle": "none", "curved": 1}}[route])
        end_h, start_h = (head if arrow in ("end", "both") else "none"), (head if arrow in ("start", "both") else "none")
        for side, h in (("end", end_h), ("start", start_h)):
            name, fill = self._HEADS[h]
            st[f"{side}Arrow"] = name
            st[f"{side}Fill"] = fill
            st[f"{side}Size"] = head_size
        if dashed:
            st.update(dashed=1, dashPattern=dash or "6 4")
        if opacity is not None:
            st["opacity"] = t.opacity(opacity)
        if exit:
            st.update(exitX=exit[0], exitY=exit[1], exitDx=0, exitDy=0)
        if entry:
            st.update(entryX=entry[0], entryY=entry[1], entryDx=0, entryDy=0)
        value = ""
        if label:
            st.update(self._font_style(None, label_size, "text", wrap=False))
            st["labelBackgroundColor"] = t.color("background")
            value = self._label(label, False)
        st.update(extra or {})
        el = dict(kind="edge", id=self._new_id(id), parent=None, style=st, tokens="", value=value,
                  src=src, tgt=tgt, pts=pts)
        self.els.append(el)
        return el["id"]

    def line(self, pts, **kw):
        kw.setdefault("arrow", None)
        return self.edge(pts, **kw)

    def arrow(self, pts, **kw):
        return self.edge(pts, arrow="end", **kw)

    def flex_arrow(self, pts, *, width=14, end_width=None, end_size=7, fill="primary", stroke=None,
                   curved=True, opacity=None, id=None):
        """Wide 'block' arrow (draw.io flexArrow). With curved=True and waypoints it becomes a wavy band."""
        t = self.theme
        st = {"html": "1", "shape": "flexArrow", "width": width, "endWidth": end_width or width,
              "endSize": end_size, "fillColor": t.color(fill), "strokeColor": t.color(stroke or fill)}
        st.update({"curved": 1, "edgeStyle": "none"} if curved else {"edgeStyle": "none"})
        if opacity is not None:
            st["opacity"] = t.opacity(opacity)
        el = dict(kind="edge", id=self._new_id(id), parent=None, style=st, tokens="", value="",
                  src=None, tgt=None, pts=[tuple(map(float, p)) for p in pts], scale_keys=("width", "endWidth", "endSize"))
        self.els.append(el)
        return el["id"]

    # ---- free-form geometry (embedded SVG) -------------------------------------------
    def _svg_paint(self, v, default="none"):
        return default if v in (None, "none") else self.theme.color(v)

    def svg_layer(self, polys, id=None, pad=2):
        """Embed free-form geometry as one SVG image element.
        polys: list of dicts with keys
            pts (list of (x,y)) | circle=(cx,cy,r)
            closed=True, smooth=False (Catmull-Rom through pts)
            fill (role/hex), fill_opacity (percent or role), stroke, stroke_opacity, sw, dash ("6 4")."""
        xs, ys = [], []
        for p in polys:
            if "circle" in p:
                cx, cy, r = p["circle"]; xs += [cx - r, cx + r]; ys += [cy - r, cy + r]
            else:
                pts = catmull_rom(p["pts"], closed=p.get("closed", True)) if p.get("smooth") else p["pts"]
                p["_pts"] = pts
                xs += [q[0] for q in pts]; ys += [q[1] for q in pts]
        x0, y0, x1, y1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
        body = []
        for p in polys:
            fill = self._svg_paint(p.get("fill"))
            stroke = self._svg_paint(p.get("stroke"))
            fo = (self.theme.opacity(p["fill_opacity"]) / 100) if p.get("fill_opacity") is not None else 1
            so = (self.theme.opacity(p["stroke_opacity"]) / 100) if p.get("stroke_opacity") is not None else 1
            sw = self.theme.stroke(p.get("sw", "normal"))
            dash = f' stroke-dasharray="{p["dash"]}"' if p.get("dash") else ""
            attrs = (f'fill="{fill}" fill-opacity="{fo:.3f}" stroke="{stroke}" stroke-opacity="{so:.3f}" '
                     f'stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"{dash}')
            if "circle" in p:
                cx, cy, r = p["circle"]
                body.append(f'<circle cx="{cx - x0:.2f}" cy="{cy - y0:.2f}" r="{r:.2f}" {attrs}/>')
            else:
                d = " ".join(f"{q[0] - x0:.2f},{q[1] - y0:.2f}" for q in p["_pts"])
                tag = "polygon" if p.get("closed", True) else "polyline"
                if tag == "polyline":
                    attrs = attrs.replace(f'fill="{fill}"', 'fill="none"') if not p.get("fill") else attrs
                body.append(f'<{tag} points="{d}" {attrs}/>')
        W, H = x1 - x0, y1 - y0
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}" height="{H:.1f}" '
               f'viewBox="0 0 {W:.2f} {H:.2f}">' + "".join(body) + "</svg>")
        b64 = base64.b64encode(svg.encode()).decode()
        st = {"shape": "image", "html": "1", "imageAspect": 0, "aspect": "fixed",
              "image": f"data:image/svg+xml,{b64}"}  # NOTE: no ';base64' — draw.io style syntax
        return self._add_vertex(id or "svg", x0, y0, W, H, "", st)

    def polygon(self, pts, *, fill="neutral", stroke="none", fill_opacity=None, stroke_opacity=None,
                sw="normal", smooth=False, closed=True, dash=None, id=None):
        return self.svg_layer([dict(pts=pts, fill=fill, stroke=stroke, fill_opacity=fill_opacity,
                                    stroke_opacity=stroke_opacity, sw=sw, smooth=smooth, closed=closed,
                                    dash=dash)], id=id)

    def surface_mesh(self, back, front, *, nu=30, nv=14, bulge=0.0, fill="secondary", fill_opacity="tint",
                     line="primary", line_opacity=55, line_width="hairline", outline="primary", id=None):
        """Pseudo-3-D surface patch (e.g. a manifold) between two edge curves, drawn as a mesh.
        back/front: control points from the left tip to the right tip (same direction).
        bulge: px to lift the middle of the patch (negative y) for a 3-D look."""
        N = 80
        B = _resample(catmull_rom(back), N + 1)
        F = _resample(catmull_rom(front), N + 1)

        def P(i, v):
            u = i / N
            x = (1 - v) * B[i][0] + v * F[i][0]
            y = (1 - v) * B[i][1] + v * F[i][1] - bulge * math.sin(math.pi * v) * math.sin(math.pi * u)
            return (x, y)
        outline_pts = [P(i, 0) for i in range(N + 1)] + [P(N - i, 1) for i in range(N + 1)]
        polys = [dict(pts=outline_pts, fill=fill, fill_opacity=fill_opacity)]
        for k in range(1, nv):
            polys.append(dict(pts=[P(i, k / nv) for i in range(N + 1)], closed=False, stroke=line,
                              stroke_opacity=line_opacity, sw=line_width))
        for k in range(1, nu):
            i = round(N * k / nu)
            polys.append(dict(pts=[P(i, j / 40) for j in range(41)], closed=False, stroke=line,
                              stroke_opacity=line_opacity, sw=line_width))
        if outline:
            polys.append(dict(pts=outline_pts, stroke=outline, stroke_opacity=80, sw="thin"))
        return self.svg_layer(polys, id=id or "surface")

    # ---- raster content ---------------------------------------------------------------
    def _source(self):
        if self._src_img is None:
            from PIL import Image
            if not self.source:
                raise ValueError("Diagram has no source image (use Diagram.from_source)")
            self._src_img = Image.open(self.source).convert("RGB")
        return self._src_img

    def crop(self, bbox, upscale=2):
        from PIL import Image
        x0, y0, x1, y1 = map(int, bbox)
        im = self._source().crop((x0, y0, x1, y1))
        if upscale and upscale != 1:
            im = im.resize((max(1, int((x1 - x0) * upscale)), max(1, int((y1 - y0) * upscale))), Image.LANCZOS)
        return im

    def save_crop(self, bbox, path, upscale=2):
        self.crop(bbox, upscale).save(path)
        return path

    def image_crop(self, bbox, x=None, y=None, w=None, h=None, *, inset=1, upscale=2, fmt="jpeg",
                   quality=85, border=None, id=None):
        """Embed a region of the source image (photo, logo, complex illustration).
        bbox=(x0,y0,x1,y1) in source px; placed at the same spot unless x/y/w/h given.
        inset trims a few px so the source's own border isn't duplicated."""
        x0, y0, x1, y1 = bbox
        im = self.crop((x0 + inset, y0 + inset, x1 - inset, y1 - inset), upscale)
        return self._embed_pil(im, x0 if x is None else x, y0 if y is None else y,
                               (x1 - x0) if w is None else w, (y1 - y0) if h is None else h,
                               fmt, quality, border, id or "image")

    def image_file(self, path, x, y, w, h, *, border=None, id=None):
        from PIL import Image
        im = Image.open(path)
        fmt = "png" if im.mode in ("RGBA", "LA", "P") else "jpeg"
        return self._embed_pil(im.convert("RGBA" if fmt == "png" else "RGB"), x, y, w, h, fmt, 90, border, id)

    def _embed_pil(self, im, x, y, w, h, fmt, quality, border, id):
        buf = io.BytesIO()
        if fmt == "jpeg":
            im.convert("RGB").save(buf, "JPEG", quality=quality)
        else:
            im.save(buf, "PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()
        st = {"shape": "image", "html": "1", "imageAspect": 0, "image": f"data:image/{fmt},{b64}"}
        if border:
            st["imageBorder"] = self.theme.color(border)
        return self._add_vertex(id, x, y, w, h, "", st)

    # ---- composites -------------------------------------------------------------------
    def callout(self, x, y, w, h, label, tip, *, base_width=40, base_at=None, fill="neutral",
                fill_opacity="soft", stroke="text", sw="normal", rounded=True, id=None, **font):
        """Speech-bubble box with a pointer toward tip=(tx,ty). The pointer leaves from the box side
        facing the tip; base_at = position along that side in px (default: nearest to tip)."""
        tx, ty = tip
        side = ("top" if ty < y else "bottom" if ty > y + h else "left" if tx < x else "right")
        horiz = side in ("top", "bottom")
        lo, hi = (x, x + w) if horiz else (y, y + h)
        c = base_at if base_at is not None else min(max(tx if horiz else ty, lo + base_width / 2 + 8), hi - base_width / 2 - 8)
        a, b = c - base_width / 2, c + base_width / 2
        edge_coord = {"top": y, "bottom": y + h, "left": x, "right": x + w}[side]
        inward = {"top": 1, "bottom": -1, "left": 1, "right": -1}[side] * (self.theme.stroke(sw) + 0.5)
        if horiz:
            p0, p1 = (a, edge_coord + inward), (b, edge_coord + inward)
        else:
            p0, p1 = (edge_coord + inward, a), (edge_coord + inward, b)
        font.setdefault("size", "body")
        with self.group(id or "callout") as gid:
            self.rect(x, y, w, h, label, fill=fill, fill_opacity=fill_opacity, stroke=stroke, sw=sw,
                      rounded=rounded, id=f"{gid}_box", spacing=6, **font)
            self.svg_layer([dict(pts=[p0, tip, p1], fill="background"),
                            dict(pts=[p0, tip, p1], fill=fill, fill_opacity=fill_opacity),
                            dict(pts=[p0, tip, p1], closed=False, stroke=stroke, sw=sw)], id=f"{gid}_pointer")
        return gid

    def panel(self, x, y, w, h, title=None, *, header_h=None, header_fill="primary", header_color="background",
              title_size="heading", title_align="center", fill="background", stroke="text", sw="normal",
              rounded=False, header_band=True, header_opacity=None, shadow=None, id=None, **font):
        """Container with an optional header band (or a plain title line if header_band=False).
        Returns (panel_id, (cx, cy, cw, ch)) where the tuple is the content area below the header."""
        pid = self.rect(x, y, w, h, fill=fill, stroke=stroke, sw=sw, rounded=rounded, shadow=shadow, id=id or "panel")
        hh = header_h or (self.theme.size(title_size) * 2.0 if title else 0)
        if title:
            if header_band:
                self.rect(x, y, w, hh, title, fill=header_fill, stroke=header_fill if stroke != "none" else "none",
                          sw=sw, fill_opacity=header_opacity, color=header_color, size=title_size, bold=True,
                          align=title_align, id=f"{pid}_header", spacing=8, **font)
            else:
                pad = self.theme.data["spacing"]["padding"]
                self.rect(x + pad, y, w - 2 * pad, hh, title, fill="none", stroke="none", color=header_color,
                          size=title_size, bold=True, align=title_align, id=f"{pid}_title", **font)
        return pid, (x, y + hh, w, h - hh)

    # ---- layout helpers -------------------------------------------------------------
    def gap(self):
        return self.theme.data["spacing"]["gap"]

    def row(self, x, y, n, w, h, gap=None):
        g = self.gap() if gap is None else gap
        return [(x + i * (w + g), y, w, h) for i in range(n)]

    def row_widths(self, x, y, widths, h, gap=None):
        """Boxes of varying widths left-to-right with one constant gap."""
        g = self.gap() if gap is None else gap
        out, cx = [], x
        for w in widths:
            out.append((cx, y, w, h)); cx += w + g
        return out

    def column(self, x, y, n, w, h, gap=None):
        g = self.gap() if gap is None else gap
        return [(x, y + i * (h + g), w, h) for i in range(n)]

    def fit_row(self, x0, x1, y, n, h, gap=None):
        """n equal boxes spanning [x0, x1] with equal gaps."""
        g = self.gap() if gap is None else gap
        w = (x1 - x0 - g * (n - 1)) / n
        return self.row(x0, y, n, w, h, g)

    def grid_boxes(self, x, y, cols, rows, w, h, gx=None, gy=None):
        gx = self.gap() if gx is None else gx
        gy = gx if gy is None else gy
        return [(x + c * (w + gx), y + r * (h + gy), w, h) for r in range(rows) for c in range(cols)]

    @staticmethod
    def snap(v, step=2):
        return round(v / step) * step

    # ---- scatter helpers --------------------------------------------------------------
    @staticmethod
    def scatter_in_polygon(poly, n, keepout=(), min_dist=8, seed=0, max_tries=200000):
        """n random points inside poly, outside keepout rects (x0,y0,x1,y1), >= min_dist apart."""
        rnd = random.Random(seed)
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        pts, tries = [], 0
        while len(pts) < n and tries < max_tries:
            tries += 1
            px, py = rnd.uniform(min(xs), max(xs)), rnd.uniform(min(ys), max(ys))
            if not point_in_polygon(px, py, poly):
                continue
            if any(a <= px <= c and b <= py <= d for a, b, c, d in keepout):
                continue
            if all((px - qx) ** 2 + (py - qy) ** 2 >= min_dist ** 2 for qx, qy in pts):
                pts.append((px, py))
        return pts

    @staticmethod
    def scatter_along(fn, x0, x1, n, spread=10, min_dist=8, seed=0, max_tries=100000):
        """n points near the curve y=fn(x), x in [x0, x1], gaussian spread in y."""
        rnd = random.Random(seed)
        pts, tries = [], 0
        while len(pts) < n and tries < max_tries:
            tries += 1
            x = rnd.uniform(x0, x1); y = fn(x) + rnd.gauss(0, spread)
            if all((x - a) ** 2 + (y - b) ** 2 >= min_dist ** 2 for a, b in pts):
                pts.append((x, y))
        return pts

    @staticmethod
    def scatter_blob(cx, cy, n, sx=20, sy=None, min_dist=8, seed=0, max_tries=100000):
        rnd = random.Random(seed)
        sy = sx if sy is None else sy
        pts, tries = [], 0
        while len(pts) < n and tries < max_tries:
            tries += 1
            x, y = rnd.gauss(cx, sx), rnd.gauss(cy, sy)
            if all((x - a) ** 2 + (y - b) ** 2 >= min_dist ** 2 for a, b in pts):
                pts.append((x, y))
        return pts

    # ---- serialization ----------------------------------------------------------------
    def _style_str(self, tokens, st, scale_keys=()):
        parts = [t for t in tokens.split(";") if t] if tokens else []
        for k, v in st.items():
            if k in ("fontSize", "arcSize") or k in scale_keys:
                v = round(float(v) * self.S, 2)
            if isinstance(v, float) and v.is_integer():
                v = int(v)
            parts.append(f"{k}={v}")
        return ";".join(parts) + ";"

    def _compute_group_bboxes(self):
        kids = {}
        for e in self.els:
            if e.get("parent"):
                kids.setdefault(e["parent"], []).append(e)
        groups = [e for e in self.els if e["kind"] == "group"]

        def bb(g):
            if "geo" in g:
                return g["geo"]
            boxes = []
            for c in kids.get(g["id"], []):
                if c["kind"] == "group":
                    if bb(c): boxes.append(bb(c))
                elif c["kind"] == "vertex":
                    boxes.append(c["geo"])
            if not boxes:
                g["geo"] = None; return None
            x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
            x1 = max(b[0] + b[2] for b in boxes); y1 = max(b[1] + b[3] for b in boxes)
            g["geo"] = [x0, y0, x1 - x0, y1 - y0]
            return g["geo"]
        for g in groups:
            bb(g)

    def to_xml(self):
        self._compute_group_bboxes()
        S = self.S
        by_id = {e["id"]: e for e in self.els}
        cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']

        def _r(v):
            v = round(v, 2)
            return int(v) if float(v).is_integer() else v

        def fx(v):
            return _r(v * S * self.cs[0])

        def fy(v):
            return _r(v * S * self.cs[1])
        f = fx
        for e in self.els:
            if e["kind"] == "group" and not e.get("geo"):
                continue
            parent = e.get("parent") or "1"
            if e["kind"] in ("vertex", "group"):
                x, y, w, h = e["geo"]
                if e.get("parent"):
                    px, py = by_id[e["parent"]]["geo"][:2]
                    x, y = x - px, y - py
                if e["kind"] == "group":
                    style = "group;"
                    extra = ' connectable="0"'
                    value = ""
                else:
                    style = self._style_str(e["tokens"], e["style"])
                    extra = ""
                    value = e["value"]
                cells.append(f'<mxCell id="{e["id"]}" value={quoteattr(value)} style={quoteattr(style)} '
                             f'vertex="1"{extra} parent="{parent}"><mxGeometry x="{fx(x)}" y="{fy(y)}" '
                             f'width="{fx(w)}" height="{fy(h)}" as="geometry"/></mxCell>')
            else:
                style = self._style_str("", e["style"], e.get("scale_keys", ()))
                a = f'id="{e["id"]}" value={quoteattr(e["value"])} style={quoteattr(style)} edge="1" parent="1"'
                if e["src"]: a += f' source="{e["src"]}"'
                if e["tgt"]: a += f' target="{e["tgt"]}"'
                pts = list(e["pts"])
                g = ""
                # pts = only the points draw.io cannot compute: a free start (no src), waypoints,
                # and a free end (no tgt). With src/tgt given, the remaining points are waypoints.
                if pts and not e["src"]:
                    g += f'<mxPoint x="{fx(pts[0][0])}" y="{fy(pts[0][1])}" as="sourcePoint"/>'
                    pts = pts[1:]
                if pts and not e["tgt"]:
                    g += f'<mxPoint x="{fx(pts[-1][0])}" y="{fy(pts[-1][1])}" as="targetPoint"/>'
                    pts = pts[:-1]
                way = pts
                if way:
                    g += '<Array as="points">' + "".join(f'<mxPoint x="{fx(x)}" y="{fy(y)}"/>' for x, y in way) + "</Array>"
                cells.append(f'<mxCell {a}><mxGeometry relative="1" as="geometry">{g}</mxGeometry></mxCell>')
        bg = self.theme.color(self.background) if self.background else "none"
        did = re.sub(r"[^\w]", "_", self.name)
        return ('<mxfile host="app.diagrams.net" agent="image-to-drawio">'
                f'<diagram id="{did}" name={quoteattr(self.name)}>'
                f'<mxGraphModel dx="{_r(self.width * S)}" dy="{_r(self.height * S)}" grid="{1 if self.grid else 0}" gridSize="10" '
                'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
                f'pageWidth="{_r(self.width * S)}" pageHeight="{_r(self.height * S)}" background="{bg}" math="{1 if self.math_enabled else 0}" shadow="0">'
                "<root>" + "".join(cells) + "</root></mxGraphModel></diagram></mxfile>")

    def save(self, path, quiet=False):
        xml = self.to_xml()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(xml)
        if not quiet:
            n_v = sum(e["kind"] == "vertex" for e in self.els)
            n_e = sum(e["kind"] == "edge" for e in self.els)
            print(f"wrote {path}  ({n_v} vertices, {n_e} edges, scale={self.S})")
            if self.theme.off_theme:
                print("  off-theme values used:", ", ".join(sorted(self.theme.off_theme)))
        return path


if __name__ == "__main__":
    print(__doc__)
