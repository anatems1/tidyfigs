#!/usr/bin/env python3
"""
inspect_image.py — measure a source figure before rebuilding it in draw.io.

Subcommands (all coordinates are SOURCE pixels):
  info    SRC                         size, background color, a few dominant colors
  grid    SRC [--step 50] [-o]        coordinate grid overlay (labels every major line)
  zoom    SRC --box X0 Y0 X1 Y1 [--factor 3] [--step 10] [-o]
                                      magnified crop with a fine grid labeled in source coords
  palette SRC [-k 8] [--theme T]      dominant colors (k-means) + swatch; maps to theme roles if given
  boxes   SRC [--min-area 150] [-o]   connected components / rectangles -> JSON + numbered overlay
  ocr     SRC [--upscale 2] [-o]      text lines with bounding boxes + estimated font px (tesseract)
  lines   SRC [--min-len 60]          long straight lines (axes, dividers, borders), needs OpenCV
  all     SRC --out-dir DIR           run everything, write DIR/summary.md (start here)

Typical use:
  python inspect_image.py all images/fig.png --out-dir images/fig_drawio_work/inspect
  python inspect_image.py zoom images/fig.png --box 40 180 200 330 --factor 4
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drawio_kit import Theme, find_font_file, measure_line  # noqa: E402


def load(src):
    return Image.open(src).convert("RGB")


def hexc(rgb):
    return "#%02x%02x%02x" % tuple(int(v) for v in rgb[:3])


def _font(px):
    p = find_font_file("Helvetica")
    return ImageFont.truetype(p, max(8, int(px))) if p else ImageFont.load_default()


def background_color(im):
    a = np.asarray(im).reshape(-1, 3)
    border = np.concatenate([np.asarray(im)[0], np.asarray(im)[-1], np.asarray(im)[:, 0], np.asarray(im)[:, -1]])
    q = (border // 8).astype(np.int32)
    keys, counts = np.unique(q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2], return_counts=True)
    k = keys[counts.argmax()]
    sel = border[(q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]) == k]
    return tuple(int(v) for v in np.median(sel, axis=0))


# ------------------------------------------------------------------ grid / zoom
def cmd_grid(src, step=50, out=None):
    im = load(src)
    W, H = im.size
    ov = im.copy()
    d = ImageDraw.Draw(ov, "RGBA")
    f = _font(max(10, min(W, H) / 70))
    for x in range(0, W, step):
        major = (x // step) % 2 == 0
        d.line([(x, 0), (x, H)], fill=(255, 0, 0, 110 if major else 55), width=1)
        if major:
            d.text((x + 2, 2), str(x), fill=(200, 0, 0, 255), font=f)
            d.text((x + 2, H - f.size - 4), str(x), fill=(200, 0, 0, 255), font=f)
    for y in range(0, H, step):
        major = (y // step) % 2 == 0
        d.line([(0, y), (W, y)], fill=(0, 0, 255, 110 if major else 55), width=1)
        if major:
            d.text((2, y + 1), str(y), fill=(0, 0, 200, 255), font=f)
            d.text((W - 4 * f.size, y + 1), str(y), fill=(0, 0, 200, 255), font=f)
    out = out or os.path.splitext(src)[0] + f".grid{step}.png"
    ov.save(out)
    print("wrote", out)
    return out


def cmd_zoom(src, box, factor=3, step=10, out=None):
    im = load(src)
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(im.width, x1), min(im.height, y1)
    crop = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * factor, (y1 - y0) * factor), Image.NEAREST)
    margin = 34
    canvas = Image.new("RGB", (crop.width + margin, crop.height + margin), "white")
    canvas.paste(crop, (margin, margin))
    d = ImageDraw.Draw(canvas, "RGBA")
    f = _font(11)
    start_x = (x0 // step + (x0 % step > 0)) * step
    for x in range(start_x, x1 + 1, step):
        X = margin + (x - x0) * factor
        major = x % (step * 5) == 0
        d.line([(X, margin), (X, canvas.height)], fill=(255, 0, 0, 140 if major else 60))
        if major or step * factor >= 40:
            d.text((X + 1, 2), str(x), fill=(200, 0, 0), font=f)
    start_y = (y0 // step + (y0 % step > 0)) * step
    for y in range(start_y, y1 + 1, step):
        Y = margin + (y - y0) * factor
        major = y % (step * 5) == 0
        d.line([(margin, Y), (canvas.width, Y)], fill=(0, 0, 255, 140 if major else 60))
        if major or step * factor >= 40:
            d.text((1, Y + 1), str(y), fill=(0, 0, 200), font=f)
    out = out or os.path.splitext(src)[0] + f".zoom_{x0}_{y0}_{x1}_{y1}.png"
    canvas.save(out)
    print("wrote", out)
    return out


# ------------------------------------------------------------------ palette
def _srgb_to_lab(rgb):
    c = np.asarray(rgb, dtype=float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def kmeans(X, k, iters=25, seed=0):
    rng = np.random.default_rng(seed)
    C = X[rng.choice(len(X), size=min(k, len(X)), replace=False)].astype(float)
    for _ in range(iters):
        d = ((X[:, None, :] - C[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        newC = np.array([X[lab == i].mean(0) if (lab == i).any() else C[i] for i in range(len(C))])
        if np.allclose(newC, C, atol=0.5):
            break
        C = newC
    return C, lab


def cmd_palette(src, k=8, theme=None, out=None, quiet=False, write=True):
    im = load(src)
    im.thumbnail((400, 400))
    X = np.asarray(im).reshape(-1, 3).astype(float)
    bg = np.array(background_color(im))
    C, lab = kmeans(X, k)
    counts = np.bincount(lab, minlength=len(C))
    order = counts.argsort()[::-1]
    rows = []
    for i in order:
        rgb = C[i]
        mx, mn = rgb.max(), rgb.min()
        sat = 0 if mx == 0 else (mx - mn) / mx
        rows.append(dict(hex=hexc(rgb), share=round(float(counts[i] / counts.sum()), 4),
                         lightness=round(float(_srgb_to_lab(rgb)[0]), 1), saturation=round(float(sat), 2),
                         is_background=bool(np.abs(rgb - bg).max() < 18)))
    th = Theme.load(theme) if theme else None
    if th:
        names = list(th.colors)
        T = _srgb_to_lab(np.array([[int(th.colors[n][j:j + 2], 16) for j in (1, 3, 5)] for n in names]))
        for r in rows:
            L = _srgb_to_lab(np.array([int(r["hex"][j:j + 2], 16) for j in (1, 3, 5)]))
            dist = np.sqrt(((T - L) ** 2).sum(-1))
            r["nearest_role"], r["delta_e"] = names[int(dist.argmin())], round(float(dist.min()), 1)
    # swatch
    sw = Image.new("RGB", (520, 34 * len(rows) + 10), "white")
    d = ImageDraw.Draw(sw)
    f = _font(14)
    for j, r in enumerate(rows):
        d.rectangle([10, 8 + 34 * j, 60, 36 + 34 * j], fill=r["hex"], outline="black")
        txt = f'{r["hex"]}  {100 * r["share"]:5.1f}%  L={r["lightness"]:5.1f}  sat={r["saturation"]:.2f}'
        if "nearest_role" in r:
            txt += f'  ~{r["nearest_role"]} (dE {r["delta_e"]})'
        if r["is_background"]:
            txt += "  [bg]"
        d.text((70, 14 + 34 * j), txt, fill="black", font=f)
    out = out or os.path.splitext(src)[0] + ".palette.png"
    if write:
        sw.save(out)
    if not quiet:
        print(f"background ~ {hexc(bg)}")
        for r in rows:
            print(" ", r)
        if write:
            print("wrote", out)
    return dict(background=hexc(bg), colors=rows, swatch=out if write else None)


# ------------------------------------------------------------------ components
def _label(mask):
    try:
        from scipy import ndimage
        lab, n = ndimage.label(mask)
        return lab, n
    except ImportError:
        pass
    try:
        import cv2
        n, lab = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)
        return lab, n - 1
    except ImportError:
        raise SystemExit("boxes needs scipy or opencv-python")


def cmd_boxes(src, min_area=150, thresh=40, out=None, quiet=False):
    """Components that differ from the background. Classifies each as filled box / outline / text-ish / mark."""
    im = load(src)
    a = np.asarray(im).astype(int)
    bg = np.array(background_color(im))
    diff = np.abs(a - bg).max(-1)
    mask = diff > thresh
    lab, n = _label(mask)
    comps = []
    if n:
        try:
            from scipy import ndimage
            slices = ndimage.find_objects(lab)
        except ImportError:
            slices = []
            for i in range(1, n + 1):
                ys, xs = np.nonzero(lab == i)
                slices.append((slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1)) if len(ys) else None)
        for i, sl in enumerate(slices, start=1):
            if sl is None:
                continue
            ys, xs = sl
            h, w = ys.stop - ys.start, xs.stop - xs.start
            region = lab[sl] == i
            area = int(region.sum())
            if w * h < min_area:
                continue
            fill_ratio = area / float(w * h)
            px = a[sl][region]
            med = np.median(px, axis=0)
            kind = ("filled box" if fill_ratio > 0.85 and min(w, h) > 12 else
                    "outline/frame" if fill_ratio < 0.25 and min(w, h) > 20 else
                    "line" if min(w, h) <= 4 else
                    "glyph/text-ish" if max(w, h) < 40 else "mark/shape")
            comps.append(dict(id=len(comps), bbox=[int(xs.start), int(ys.start), int(xs.stop), int(ys.stop)],
                              w=int(w), h=int(h), area=area, fill_ratio=round(fill_ratio, 2),
                              color=hexc(med), kind=kind))
    comps.sort(key=lambda c: -c["w"] * c["h"])
    for j, c in enumerate(comps):
        c["id"] = j
    ov = im.copy()
    d = ImageDraw.Draw(ov, "RGBA")
    f = _font(12)
    for c in comps[:300]:
        if c["kind"] == "glyph/text-ish":
            continue
        x0, y0, x1, y1 = c["bbox"]
        col = {"filled box": (0, 160, 0, 200), "outline/frame": (220, 0, 0, 200), "line": (0, 0, 220, 200)}.get(c["kind"], (200, 120, 0, 200))
        d.rectangle([x0, y0, x1, y1], outline=col, width=2)
        d.text((x0 + 2, y0 + 1), str(c["id"]), fill=col, font=f)
    out = out or os.path.splitext(src)[0] + ".boxes.png"
    ov.save(out)
    js = os.path.splitext(out)[0] + ".json"
    json.dump(dict(background=hexc(bg), components=comps), open(js, "w"), indent=1)
    if not quiet:
        print(f"{len(comps)} components (background {hexc(bg)}); wrote {out} and {js}")
        for c in comps[:40]:
            if c["kind"] != "glyph/text-ish":
                print(" ", c)
    return comps, out, js


def cmd_lines(src, min_len=60, quiet=False):
    try:
        import cv2
    except ImportError:
        print("lines needs opencv-python; skipping")
        return []
    g = cv2.cvtColor(np.asarray(load(src)), cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(g, 50, 150)
    L = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60, minLineLength=min_len, maxLineGap=4)
    out = []
    for l in (L if L is not None else []):
        x1, y1, x2, y2 = map(int, l[0])
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180
        kind = "horizontal" if ang < 2 or ang > 178 else "vertical" if abs(ang - 90) < 2 else "diagonal"
        out.append(dict(p1=[x1, y1], p2=[x2, y2], length=round(math.dist((x1, y1), (x2, y2))), kind=kind))
    out.sort(key=lambda r: -r["length"])
    if not quiet:
        for r in out[:40]:
            print(" ", r)
    return out


# ------------------------------------------------------------------ OCR
def cmd_ocr(src, upscale=2, out=None, quiet=False, psm=11, family="Helvetica"):
    try:
        import pytesseract
    except ImportError:
        print("ocr needs pytesseract + tesseract; skipping (read the text visually instead)")
        return []
    im = load(src)
    big = im.resize((im.width * upscale, im.height * upscale), Image.LANCZOS)
    data = pytesseract.image_to_data(big, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    words = []
    for i, t in enumerate(data["text"]):
        if t.strip() and float(data["conf"][i]) > 30:
            words.append(dict(text=t, x=data["left"][i] / upscale, y=data["top"][i] / upscale,
                              w=data["width"][i] / upscale, h=data["height"][i] / upscale,
                              key=(data["block_num"][i], data["par_num"][i], data["line_num"][i])))
    # Also run inverted pass for white/light text on dark backgrounds
    try:
        from PIL import ImageOps
        inv = ImageOps.invert(big.convert("L"))
        data_inv = pytesseract.image_to_data(inv, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
        for i, t in enumerate(data_inv["text"]):
            if t.strip() and float(data_inv["conf"][i]) > 30:
                ix = data_inv["left"][i] / upscale
                iy = data_inv["top"][i] / upscale
                iw = data_inv["width"][i] / upscale
                ih = data_inv["height"][i] / upscale
                overlap = any(abs(ix - w["x"]) < max(iw, w["w"]) * 0.7 and abs(iy - w["y"]) < max(ih, w["h"]) * 0.7 for w in words)
                if not overlap:
                    words.append(dict(text=t, x=ix, y=iy, w=iw, h=ih,
                                      key=(100 + data_inv["block_num"][i], data_inv["par_num"][i], data_inv["line_num"][i])))
    except Exception:
        pass
    # group by tesseract line, then merge horizontally adjacent words at the same baseline
    lines = {}
    for w in words:
        lines.setdefault(w["key"], []).append(w)
    rows = []
    for ws in lines.values():
        ws.sort(key=lambda w: w["x"])
        cur = [ws[0]]
        for w in ws[1:]:
            prev = cur[-1]
            if w["x"] - (prev["x"] + prev["w"]) < 1.2 * max(prev["h"], w["h"]) and abs(w["y"] - prev["y"]) < 0.6 * prev["h"]:
                cur.append(w)
            else:
                rows.append(cur); cur = [w]
        rows.append(cur)
    res = []
    for r in rows:
        x0 = min(w["x"] for w in r); y0 = min(w["y"] for w in r)
        x1 = max(w["x"] + w["w"] for w in r); y1 = max(w["y"] + w["h"] for w in r)
        text = " ".join(w["text"] for w in r)
        has_desc = any(ch in text for ch in "gjpqy(),;")
        caps = text.upper() == text
        est = (y1 - y0) / (1.04 if has_desc else 0.74 if caps else 0.84)   # calibrated on Helvetica/Arial
        # width-based estimate (more robust when OCR text is right): size where measured width == bbox width
        w100 = measure_line([dict(text=text)], family, 100) or 1
        b100 = measure_line([dict(text=text, bold=True)], family, 100) or 1
        res.append(dict(text=text, bbox=[round(x0), round(y0), round(x1), round(y1)],
                        center=[round((x0 + x1) / 2), round((y0 + y1) / 2)], est_font_px=round(est, 1),
                        est_px_if_regular=round(100 * (x1 - x0) / w100, 1),
                        est_px_if_bold=round(100 * (x1 - x0) / b100, 1)))
    res.sort(key=lambda r: (r["bbox"][1] // 8, r["bbox"][0]))
    ov = im.copy()
    d = ImageDraw.Draw(ov, "RGBA")
    f = _font(10)
    for j, r in enumerate(res):
        d.rectangle(r["bbox"], outline=(255, 0, 255, 200), width=1)
        d.text((r["bbox"][0], r["bbox"][3]), f"{j}:{r['est_font_px']:.0f}", fill=(200, 0, 200), font=f)
    out = out or os.path.splitext(src)[0] + ".ocr.png"
    ov.save(out)
    js = os.path.splitext(out)[0] + ".json"
    json.dump(res, open(js, "w"), indent=1)
    if not quiet:
        for j, r in enumerate(res):
            print(f"  [{j}] {r['bbox']} ~{r['est_font_px']}px (width fit: {r['est_px_if_regular']} reg / {r['est_px_if_bold']} bold)  {r['text']}")
        print("wrote", out, js)
    return res


# ------------------------------------------------------------------ all
def cmd_all(src, out_dir, theme=None, step=None):
    os.makedirs(out_dir, exist_ok=True)
    im = load(src)
    W, H = im.size
    step = step or (25 if max(W, H) <= 700 else 50 if max(W, H) <= 1600 else 100)
    stem = os.path.join(out_dir, "source")
    im.save(stem + ".png")
    grid = cmd_grid(stem + ".png", step, stem + f".grid{step}.png")
    fine = cmd_grid(stem + ".png", max(10, step // 2), stem + f".grid{max(10, step // 2)}.png")
    pal = cmd_palette(stem + ".png", 10, theme, stem + ".palette.png", quiet=True)
    comps, boxes_png, boxes_js = cmd_boxes(stem + ".png", out=stem + ".boxes.png", quiet=True)
    ocr = cmd_ocr(stem + ".png", out=stem + ".ocr.png", quiet=True)
    lines = cmd_lines(stem + ".png", quiet=True)
    md = [f"# Inspection summary for `{src}`", "",
          f"- size: **{W} x {H}** px, background ~ `{pal['background']}`",
          f"- grids: `{os.path.basename(grid)}` (step {step}), `{os.path.basename(fine)}`",
          f"- palette swatch: `{os.path.basename(pal['swatch'])}`  |  boxes: `{os.path.basename(boxes_png)}`"
          f"  |  OCR: `source.ocr.png`", "",
          "## Palette (largest share first)", "", "| hex | share | L | sat | note |", "|---|---|---|---|---|"]
    for c in pal["colors"]:
        note = ("background" if c["is_background"] else "") + (f" ~{c['nearest_role']} dE={c['delta_e']}" if "nearest_role" in c else "")
        md.append(f"| `{c['hex']}` | {100 * c['share']:.1f}% | {c['lightness']} | {c['saturation']} | {note} |")
    md += ["", "## Large components (candidate boxes/panels/lines)", "", "| id | bbox x0,y0,x1,y1 | w x h | kind | color |", "|---|---|---|---|---|"]
    for c in [c for c in comps if c["kind"] != "glyph/text-ish"][:60]:
        md.append(f"| {c['id']} | {c['bbox']} | {c['w']}x{c['h']} | {c['kind']} | `{c['color']}` |")
    if lines:
        md += ["", "## Long straight lines", ""] + [f"- {l['kind']} {l['p1']} -> {l['p2']} (len {l['length']})" for l in lines[:30]]
    if ocr:
        sizes = sorted({round(r["est_font_px"]) for r in ocr})
        md += ["", f"## OCR text lines (est. font px; distinct ~ {sizes})", "",
               "| # | bbox | center | ~px (height) | px if regular / bold (width fit) | text |", "|---|---|---|---|---|---|"]
        for j, r in enumerate(ocr):
            md.append(f"| {j} | {r['bbox']} | {r['center']} | {r['est_font_px']} | {r['est_px_if_regular']} / {r['est_px_if_bold']} | {r['text'].replace('|', '/')} |")
        md += ["", "> OCR can misread; always confirm text visually. Prefer the width-fit size when the OCR text is",
               "> correct (pick the regular or bold column by looking); the height estimate is +/-15%."]
    else:
        md += ["", "_OCR unavailable — transcribe text by viewing the image._"]
    path = os.path.join(out_dir, "summary.md")
    open(path, "w").write("\n".join(md) + "\n")
    print("wrote", path)
    return path


def cmd_probe(src, box, ascii_map=True):
    """Deep inspect a region (x0, y0, x1, y1): dominant colors, shapes, text, and ASCII map."""
    im = load(src)
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(im.width, x1), min(im.height, y1)
    crop = im.crop((x0, y0, x1, y1))
    arr = np.asarray(crop)
    h, w = arr.shape[:2]
    print(f"=== Probe region [{x0}, {y0}, {x1}, {y1}] ({w}x{h} px) ===")

    # 1. Colors
    pixels = arr.reshape(-1, 3)
    u_colors, counts = np.unique(pixels, axis=0, return_counts=True)
    idx = np.argsort(-counts)
    print("Top colors (RGB):")
    for i in range(min(5, len(idx))):
        c = u_colors[idx[i]]
        print(f"  #{c[0]:02x}{c[1]:02x}{c[2]:02x} ({c}): {counts[idx[i]]} px ({counts[idx[i]]/(w*h)*100:.1f}%)")

    # 2. Text in this box (normal and inverted)
    try:
        import pytesseract
        from PIL import ImageOps
        txt_norm = pytesseract.image_to_string(crop).strip()
        txt_inv = pytesseract.image_to_string(ImageOps.invert(crop.convert("L"))).strip()
        if txt_norm:
            print(f"Text (normal): '{txt_norm}'")
        if txt_inv and txt_inv != txt_norm:
            print(f"Text (inverted): '{txt_inv}'")
    except Exception:
        pass

    # 3. Geometric features (OpenCV if available)
    try:
        import cv2
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 10, param1=50, param2=20, minRadius=5, maxRadius=max(w, h))
        if circles is not None:
            print(f"Circles detected: {len(circles[0])}")
            for c in circles[0][:5]:
                print(f"  circle: center=({c[0]+x0:.1f}, {c[1]+y0:.1f}), r={c[2]:.1f}")
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 15, minLineLength=15, maxLineGap=4)
        if lines is not None:
            print(f"Lines detected: {len(lines)}")
            for l in lines[:5]:
                lx1, ly1, lx2, ly2 = l[0]
                print(f"  line: ({lx1+x0}, {ly1+y0}) -> ({lx2+x0}, {ly2+y0}) len={math.hypot(lx2-lx1, ly2-ly1):.1f}")
    except Exception:
        pass

    # 4. ASCII Density Map
    if ascii_map:
        grid_h = min(25, max(5, h // 2))
        grid_w = min(60, max(10, w // 2))
        small = crop.convert("L").resize((grid_w, grid_h), Image.BILINEAR)
        sm_arr = np.asarray(small)
        print("ASCII density map:")
        for r in range(grid_h):
            line = "".join("#" if sm_arr[r, c] < 80 else "+" if sm_arr[r, c] < 160 else "." if sm_arr[r, c] < 230 else " " for c in range(grid_w))
            print(f"  {line}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info"); p.add_argument("src")
    p = sub.add_parser("grid"); p.add_argument("src"); p.add_argument("--step", type=int, default=50); p.add_argument("-o", "--out")
    p = sub.add_parser("zoom"); p.add_argument("src"); p.add_argument("--box", type=float, nargs=4, required=True)
    p.add_argument("--factor", type=int, default=3); p.add_argument("--step", type=int, default=10); p.add_argument("-o", "--out")
    p = sub.add_parser("palette"); p.add_argument("src"); p.add_argument("-k", type=int, default=8); p.add_argument("--theme"); p.add_argument("-o", "--out")
    p = sub.add_parser("boxes"); p.add_argument("src"); p.add_argument("--min-area", type=int, default=150)
    p.add_argument("--thresh", type=int, default=40); p.add_argument("-o", "--out")
    p = sub.add_parser("ocr"); p.add_argument("src"); p.add_argument("--upscale", type=int, default=2); p.add_argument("--psm", type=int, default=11); p.add_argument("-o", "--out")
    p = sub.add_parser("lines"); p.add_argument("src"); p.add_argument("--min-len", type=int, default=60)
    p = sub.add_parser("probe"); p.add_argument("src"); p.add_argument("--box", type=float, nargs=4, required=True)
    p.add_argument("--no-ascii", action="store_true")
    p = sub.add_parser("all"); p.add_argument("src"); p.add_argument("--out-dir", required=True); p.add_argument("--theme"); p.add_argument("--step", type=int)
    a = ap.parse_args()
    if a.cmd == "info":
        im = load(a.src)
        print(f"size {im.width}x{im.height}, background ~ {hexc(background_color(im))}")
        cmd_palette(a.src, 6, write=False)
    elif a.cmd == "grid":
        cmd_grid(a.src, a.step, a.out)
    elif a.cmd == "zoom":
        cmd_zoom(a.src, a.box, a.factor, a.step, a.out)
    elif a.cmd == "palette":
        cmd_palette(a.src, a.k, a.theme, a.out)
    elif a.cmd == "boxes":
        cmd_boxes(a.src, a.min_area, a.thresh, a.out)
    elif a.cmd == "ocr":
        cmd_ocr(a.src, a.upscale, a.out, psm=a.psm)
    elif a.cmd == "lines":
        cmd_lines(a.src, a.min_len)
    elif a.cmd == "probe":
        cmd_probe(a.src, a.box, ascii_map=not a.no_ascii)
    elif a.cmd == "all":
        cmd_all(a.src, a.out_dir, a.theme, a.step)


if __name__ == "__main__":
    main()
