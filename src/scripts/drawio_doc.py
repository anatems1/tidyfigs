"""
drawio_doc — load, inspect and edit an EXISTING .drawio file (any origin: image-to-drawio,
text-to-drawio, hand-made). Complements drawio_kit (which builds new diagrams).

    from drawio_doc import Doc
    doc = Doc.load("fig.drawio")
    for c in doc.vertices(): print(c.id, c.plain, c.style.get("fillColor"))
    doc.find(text="Encoder")[0].set_style(fillColor="#19355d", fontColor="#ffffff")
    doc.move("box1", dx=4); doc.align(["a", "b", "c"], "top"); doc.distribute(["a", "b", "c"], "x")
    doc.save("fig#ENHANCED.drawio")

Geometry helpers work in ABSOLUTE page coordinates (children of groups are converted for you).
Styles are dicts; base tokens (e.g. "text", "ellipse", "group") are kept in Cell.tokens.
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import base64
import copy
import html
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

__all__ = ["Doc", "Cell", "parse_style", "style_to_str", "plain_text"]


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


def style_to_str(tokens, kv):
    parts = list(tokens) + [f"{k}={v}" for k, v in kv.items()]
    return ";".join(parts) + (";" if parts else "")


def plain_text(value):
    v = re.sub(r"<br\s*/?>", "\n", value or "")
    v = re.sub(r"</(div|p)>", "\n", v)
    return html.unescape(re.sub(r"<[^>]+>", "", v)).strip()


class Cell:
    def __init__(self, doc, el, wrapper=None):
        self.doc, self.el, self.wrapper = doc, el, wrapper
        self.tokens, self.style = parse_style(el.get("style"))

    # identity / kind
    @property
    def id(self):
        return (self.wrapper if self.wrapper is not None else self.el).get("id")

    @property
    def is_vertex(self):
        return self.el.get("vertex") == "1"

    @property
    def is_edge(self):
        return self.el.get("edge") == "1"

    @property
    def is_group(self):
        return "group" in self.tokens

    @property
    def is_text(self):
        return "text" in self.tokens

    @property
    def is_image(self):
        return self.style.get("shape") == "image"

    @property
    def is_math(self):
        return bool(re.fullmatch(r"\s*\$\$.+\$\$\s*", self.plain, re.S))

    @property
    def parent(self):
        return self.el.get("parent")

    @property
    def value(self):
        w = self.wrapper
        return (w.get("label") if w is not None else self.el.get("value")) or ""

    @value.setter
    def value(self, v):
        (self.wrapper if self.wrapper is not None else self.el).set("label" if self.wrapper is not None else "value", v)

    @property
    def plain(self):
        return plain_text(self.value)

    # style
    def set_style(self, **kv):
        for k, v in kv.items():
            if v is None:
                self.style.pop(k, None)
            else:
                self.style[k] = str(v)
        self._flush()
        return self

    def get(self, k, default=None):
        return self.style.get(k, default)

    def _flush(self):
        self.el.set("style", style_to_str(self.tokens, self.style))

    # geometry
    @property
    def geo_el(self):
        return self.el.find("mxGeometry")

    def rel_geo(self):
        g = self.geo_el
        if g is None:
            return None
        return [float(g.get(k, 0) or 0) for k in ("x", "y", "width", "height")]

    def abs_geo(self):
        g = self.rel_geo()
        if g is None:
            return None
        p = self.doc.get(self.parent) if self.parent not in (None, "0", "1") else None
        if p is not None and p.is_vertex:
            pg = p.abs_geo()
            if pg:
                g[0] += pg[0]; g[1] += pg[1]
        return g

    def set_abs_geo(self, x=None, y=None, w=None, h=None):
        g = self.geo_el
        cur = self.abs_geo()
        rel = self.rel_geo()
        ox, oy = cur[0] - rel[0], cur[1] - rel[1]
        if x is not None: g.set("x", _fmt(x - ox))
        if y is not None: g.set("y", _fmt(y - oy))
        if w is not None: g.set("width", _fmt(w))
        if h is not None: g.set("height", _fmt(h))
        return self

    def __repr__(self):
        kind = "edge" if self.is_edge else "group" if self.is_group else "text" if self.is_text else "vertex"
        return f"<{kind} {self.id} {self.plain[:30]!r}>"


def _fmt(v):
    v = round(float(v), 2)
    return str(int(v)) if v.is_integer() else str(v)


class Doc:
    def __init__(self, tree, root_el, model, diagram, compressed):
        self.tree, self.root_el, self.model, self.diagram, self.compressed = tree, root_el, model, diagram, compressed
        self._index()

    # ---------- io
    @classmethod
    def load(cls, path):
        tree = ET.parse(path)
        top = tree.getroot()
        if top.tag == "mxGraphModel":
            return cls(tree, top, top, None, False)
        diag = top.find("diagram")
        model = diag.find("mxGraphModel")
        compressed = False
        if model is None:
            data = base64.b64decode(diag.text.strip())
            model = ET.fromstring(urllib.parse.unquote(zlib.decompress(data, -15).decode()))
            diag.text = None
            diag.append(model)
            compressed = True
        return cls(tree, top, model, diag, compressed)

    def save(self, path):
        self._index()
        self.tree.write(path, encoding="utf-8", xml_declaration=False)
        return path

    def _index(self):
        self.root = self.model.find("root")
        self.cells, self._by = [], {}
        for o in list(self.root):
            if o.tag == "mxCell":
                c = Cell(self, o)
            else:
                inner = o.find("mxCell")
                if inner is None:
                    continue
                c = Cell(self, inner, wrapper=o)
            self.cells.append(c)
            self._by[c.id] = c

    # ---------- query
    def get(self, cid):
        return self._by.get(cid)

    def vertices(self, include_groups=False):
        return [c for c in self.cells if c.is_vertex and (include_groups or not c.is_group)]

    def edges(self):
        return [c for c in self.cells if c.is_edge]

    def find(self, text=None, style=None, kind=None):
        """text: regex on plain label; style: dict of key->value (or regex string) that must match."""
        out = []
        for c in self.cells:
            if kind == "vertex" and not c.is_vertex: continue
            if kind == "edge" and not c.is_edge: continue
            if kind == "text" and not c.is_text: continue
            if text and not re.search(text, c.plain, re.I): continue
            if style and not all(re.fullmatch(str(v), c.style.get(k, "")) for k, v in style.items()): continue
            out.append(c)
        return out

    @property
    def page(self):
        return float(self.model.get("pageWidth", 850)), float(self.model.get("pageHeight", 1100))

    def set_page(self, w, h):
        self.model.set("pageWidth", _fmt(w)); self.model.set("pageHeight", _fmt(h))
        self.model.set("dx", _fmt(w)); self.model.set("dy", _fmt(h))

    @property
    def math(self):
        return self.model.get("math") == "1"

    @math.setter
    def math(self, on):
        self.model.set("math", "1" if on else "0")

    def content_bbox(self):
        boxes = [c.abs_geo() for c in self.vertices() if c.abs_geo()]
        for e in self.edges():
            for p in e.el.iter("mxPoint"):
                if p.get("as") in ("sourcePoint", "targetPoint", None):
                    x, y = float(p.get("x", 0)), float(p.get("y", 0))
                    boxes.append([x, y, 0, 0])
        if not boxes:
            return [0, 0, 0, 0]
        x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
        x1 = max(b[0] + b[2] for b in boxes); y1 = max(b[1] + b[3] for b in boxes)
        return [x0, y0, x1 - x0, y1 - y0]

    # ---------- edit
    def move(self, cid, dx=0, dy=0):
        c = self.get(cid)
        g = c.abs_geo()
        c.set_abs_geo(x=g[0] + dx, y=g[1] + dy)
        return c

    def translate_all(self, dx, dy):
        """Shift every top-level vertex and every free edge point / waypoint."""
        for c in self.cells:
            if c.is_vertex and c.parent in ("1", None):
                g = c.geo_el
                g.set("x", _fmt(float(g.get("x", 0)) + dx)); g.set("y", _fmt(float(g.get("y", 0)) + dy))
            elif c.is_edge and c.parent in ("1", None):
                for p in c.el.iter("mxPoint"):
                    p.set("x", _fmt(float(p.get("x", 0)) + dx)); p.set("y", _fmt(float(p.get("y", 0)) + dy))

    def align(self, ids, edge="top"):
        """Align vertices on left|right|top|bottom|center-x|center-y to their mean."""
        cs = [self.get(i) for i in ids]
        gs = [c.abs_geo() for c in cs]
        f = {"left": lambda g: g[0], "right": lambda g: g[0] + g[2], "center-x": lambda g: g[0] + g[2] / 2,
             "top": lambda g: g[1], "bottom": lambda g: g[1] + g[3], "center-y": lambda g: g[1] + g[3] / 2}[edge]
        target = sum(f(g) for g in gs) / len(gs)
        for c, g in zip(cs, gs):
            d = target - f(g)
            if edge in ("left", "right", "center-x"):
                c.set_abs_geo(x=g[0] + d)
            else:
                c.set_abs_geo(y=g[1] + d)

    def distribute(self, ids, axis="x"):
        """Equal gaps between vertices (sorted by position) keeping the first and last fixed."""
        cs = sorted((self.get(i) for i in ids), key=lambda c: c.abs_geo()[0 if axis == "x" else 1])
        gs = [c.abs_geo() for c in cs]
        k = 0 if axis == "x" else 1
        span = gs[-1][k] + gs[-1][k + 2] - gs[0][k]
        total = sum(g[k + 2] for g in gs)
        gap = (span - total) / (len(gs) - 1) if len(gs) > 1 else 0
        pos = gs[0][k]
        for c, g in zip(cs, gs):
            c.set_abs_geo(**({"x": pos} if axis == "x" else {"y": pos}))
            pos += g[k + 2] + gap

    def equalize(self, ids, width=True, height=True, anchor="center"):
        cs = [self.get(i) for i in ids]
        gs = [c.abs_geo() for c in cs]
        W = max(g[2] for g in gs); H = max(g[3] for g in gs)
        for c, g in zip(cs, gs):
            nw, nh = (W if width else g[2]), (H if height else g[3])
            nx = g[0] - (nw - g[2]) / 2 if anchor == "center" else g[0]
            ny = g[1] - (nh - g[3]) / 2 if anchor == "center" else g[1]
            c.set_abs_geo(nx, ny, nw, nh)

    def remove(self, cid):
        c = self.get(cid)
        if c is None:
            return
        kids = [k.id for k in self.cells if k.parent == cid]
        for k in kids:
            self.remove(k)
        self.root.remove(c.wrapper if c.wrapper is not None else c.el)
        for e in self.edges():  # detach edges pointing to it
            for side in ("source", "target"):
                if e.el.get(side) == cid:
                    del e.el.attrib[side]
        self._index()

    def add_vertex(self, cid, value, style, x, y, w, h, parent="1"):
        el = ET.SubElement(self.root, "mxCell", id=cid, value=value, style=style, vertex="1", parent=parent)
        ET.SubElement(el, "mxGeometry", x=_fmt(x), y=_fmt(y), width=_fmt(w), height=_fmt(h), **{"as": "geometry"})
        self._index()
        return self.get(cid)

    def add_edge(self, cid, style, src=None, tgt=None, points=(), source_point=None, target_point=None, value=""):
        attrs = dict(id=cid, value=value, style=style, edge="1", parent="1")
        if src: attrs["source"] = src
        if tgt: attrs["target"] = tgt
        el = ET.SubElement(self.root, "mxCell", **attrs)
        g = ET.SubElement(el, "mxGeometry", relative="1", **{"as": "geometry"})
        if source_point:
            ET.SubElement(g, "mxPoint", x=_fmt(source_point[0]), y=_fmt(source_point[1]), **{"as": "sourcePoint"})
        if target_point:
            ET.SubElement(g, "mxPoint", x=_fmt(target_point[0]), y=_fmt(target_point[1]), **{"as": "targetPoint"})
        if points:
            arr = ET.SubElement(g, "Array", **{"as": "points"})
            for px, py in points:
                ET.SubElement(arr, "mxPoint", x=_fmt(px), y=_fmt(py))
        self._index()
        return self.get(cid)

    def new_id(self, base="enh"):
        i = 1
        while f"{base}_{i}" in self._by:
            i += 1
        return f"{base}_{i}"

    def clone(self):
        return Doc(copy.deepcopy(self.tree), None, None, None, self.compressed)._reattach()

    def _reattach(self):
        top = self.tree.getroot()
        self.root_el = top
        if top.tag == "mxGraphModel":
            self.model, self.diagram = top, None
        else:
            self.diagram = top.find("diagram"); self.model = self.diagram.find("mxGraphModel")
        self._index()
        return self
