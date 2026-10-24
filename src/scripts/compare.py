#!/usr/bin/env python3
"""
compare.py — quantify and visualize how closely a rebuilt diagram matches the source image.

    python compare.py SOURCE.png PREVIEW.png --out-dir work/compare --tag iter_03
    python compare.py SOURCE.png fig.drawio  --out-dir work/compare          # renders the .drawio first

Writes (prefix = tag):
  <tag>_side.png      source | preview side by side, shared coordinate grid
  <tag>_overlay.png   50/50 blend (ghosting = misalignment)
  <tag>_edges.png     source edges RED, preview edges CYAN, matches WHITE/GRAY  <- best for alignment work
  <tag>_heat.png      per-cell mismatch heatmap with cell coordinates (worst cells outlined)
  <tag>_metrics.json  scores + worst cells (in source px) — use the boxes with `inspect_image.py zoom`

Scores (0..1, higher is better):
  pixel_similarity  1 - mean |gray difference| (after slight blur) — color/fill agreement
  edge_f1           F1 of edge pixels within a 3 px tolerance — geometry/text placement agreement
  score             0.4 * pixel_similarity + 0.6 * edge_f1
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drawio_kit import find_font_file  # noqa: E402


def _font(px):
    p = find_font_file("Helvetica")
    return ImageFont.truetype(p, max(8, int(px))) if p else ImageFont.load_default()


def edges(gray):
    try:
        import cv2
        return cv2.Canny(gray, 60, 160) > 0
    except ImportError:
        g = gray.astype(float)
        gx = np.zeros_like(g); gy = np.zeros_like(g)
        gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
        gy[1:-1, :] = g[2:, :] - g[:-2, :]
        mag = np.hypot(gx, gy)
        return mag > max(40, np.percentile(mag, 90))


def dilate(mask, r):
    try:
        from scipy import ndimage
        return ndimage.binary_dilation(mask, iterations=r)
    except ImportError:
        out = mask.copy()
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                out |= np.roll(np.roll(mask, dy, 0), dx, 1)
        return out


def compare(src_path, prev_path, out_dir, tag="cmp", cell=None, tol=3, quiet=False):
    os.makedirs(out_dir, exist_ok=True)
    if prev_path.endswith(".drawio"):
        from render_preview import render_kit
        rendered = os.path.join(out_dir, f"{tag}_preview.png")
        with Image.open(src_path) as s:
            render_kit(prev_path, rendered, width=s.width)
        prev_path = rendered
    A = Image.open(src_path).convert("RGB")
    B = Image.open(prev_path).convert("RGB")
    if B.size != A.size:
        B = B.resize(A.size, Image.LANCZOS)
    W, H = A.size
    ga = np.asarray(A.convert("L").filter(ImageFilter.GaussianBlur(1.2))).astype(float)
    gb = np.asarray(B.convert("L").filter(ImageFilter.GaussianBlur(1.2))).astype(float)
    diff = np.abs(ga - gb) / 255.0
    pix = 1 - diff.mean()
    ea, eb = edges(np.asarray(A.convert("L"))), edges(np.asarray(B.convert("L")))
    da, db = dilate(ea, tol), dilate(eb, tol)
    prec = (eb & da).sum() / max(1, eb.sum())
    rec = (ea & db).sum() / max(1, ea.sum())
    f1 = 2 * prec * rec / max(1e-9, prec + rec)
    score = 0.4 * pix + 0.6 * f1

    # per-cell scores
    cell = cell or max(40, int(round(max(W, H) / 14 / 10) * 10))
    cells = []
    for y in range(0, H, cell):
        for x in range(0, W, cell):
            sl = (slice(y, min(H, y + cell)), slice(x, min(W, x + cell)))
            ca, cb = ea[sl], eb[sl]
            if ca.sum() + cb.sum() < 30 and diff[sl].mean() < 0.03:
                continue
            p = (cb & da[sl]).sum() / max(1, cb.sum()); r = (ca & db[sl]).sum() / max(1, ca.sum())
            cf1 = 2 * p * r / max(1e-9, p + r)
            cpix = 1 - diff[sl].mean()
            cells.append(dict(box=[x, y, min(W, x + cell), min(H, y + cell)], edge_f1=round(float(cf1), 3),
                              pixel=round(float(cpix), 3), bad=round(float(1 - (0.4 * cpix + 0.6 * cf1)), 3),
                              missing_edges=int((ca & ~db[sl]).sum()), extra_edges=int((cb & ~da[sl]).sum())))
    worst = sorted(cells, key=lambda c: -c["bad"])[:8]

    # visuals
    f = _font(max(11, W / 90))
    side = Image.new("RGB", (W * 2 + 10, H), "white")
    side.paste(A, (0, 0)); side.paste(B, (W + 10, 0))
    d = ImageDraw.Draw(side, "RGBA")
    step = 50 if max(W, H) <= 1600 else 100
    for off in (0, W + 10):
        for x in range(0, W, step):
            d.line([(off + x, 0), (off + x, H)], fill=(255, 0, 0, 40))
            if (x // step) % 2 == 0:
                d.text((off + x + 2, 2), str(x), fill=(200, 0, 0, 200), font=f)
        for y in range(0, H, step):
            d.line([(off, y), (off + W, y)], fill=(0, 0, 255, 40))
            if (y // step) % 2 == 0:
                d.text((off + 2, y + 1), str(y), fill=(0, 0, 200, 200), font=f)
    d.text((W - 90, H - 24), "SOURCE", fill=(200, 0, 0), font=f)
    d.text((2 * W - 80, H - 24), "PREVIEW", fill=(0, 120, 200), font=f)
    side_p = os.path.join(out_dir, f"{tag}_side.png"); side.save(side_p)
    over_p = os.path.join(out_dir, f"{tag}_overlay.png"); Image.blend(A, B, 0.5).save(over_p)
    e = np.full((H, W, 3), 255, np.uint8)
    e[ea & ~db] = (230, 0, 0)          # in source only (missing in preview)
    e[eb & ~da] = (0, 170, 220)        # in preview only (extra / misplaced)
    e[ea & db] = (90, 90, 90)          # matched
    edges_p = os.path.join(out_dir, f"{tag}_edges.png"); Image.fromarray(e).save(edges_p)
    heat = A.convert("L").convert("RGB")
    hd = ImageDraw.Draw(heat, "RGBA")
    for c in cells:
        a = int(200 * min(1, c["bad"] * 1.6))
        hd.rectangle(c["box"], fill=(255, 0, 0, a // 2))
    for i, c in enumerate(worst):
        hd.rectangle(c["box"], outline=(255, 0, 0, 255), width=3)
        hd.text((c["box"][0] + 3, c["box"][1] + 2), f"#{i + 1} {c['box'][0]},{c['box'][1]}", fill=(120, 0, 0), font=f)
    heat_p = os.path.join(out_dir, f"{tag}_heat.png"); heat.save(heat_p)

    metrics = dict(tag=tag, source=src_path, preview=prev_path, pixel_similarity=round(float(pix), 4),
                   edge_precision=round(float(prec), 4), edge_recall=round(float(rec), 4),
                   edge_f1=round(float(f1), 4), score=round(float(score), 4), cell_size=cell, worst_cells=worst,
                   images=dict(side=side_p, overlay=over_p, edges=edges_p, heat=heat_p))
    json.dump(metrics, open(os.path.join(out_dir, f"{tag}_metrics.json"), "w", encoding="utf-8"), indent=1)
    if not quiet:
        print(f"[{tag}] score={score:.3f}  pixel={pix:.3f}  edge_f1={f1:.3f} (precision {prec:.3f}, recall {rec:.3f})")
        print("  worst cells (x0,y0,x1,y1): " + "; ".join(f"{c['box']} bad={c['bad']}" for c in worst[:5]))
        print("  images:", side_p, edges_p, heat_p)
    return metrics


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source"); ap.add_argument("preview", help="PNG preview or .drawio file")
    ap.add_argument("--out-dir", default="compare"); ap.add_argument("--tag", default="cmp")
    ap.add_argument("--cell", type=int, default=None); ap.add_argument("--tol", type=int, default=3)
    a = ap.parse_args()
    compare(a.source, a.preview, a.out_dir, a.tag, a.cell, a.tol)


if __name__ == "__main__":
    main()
