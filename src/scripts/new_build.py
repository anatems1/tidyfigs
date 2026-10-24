#!/usr/bin/env python3
"""
new_build.py — scaffold a work directory for converting one image to .drawio.

    python new_build.py ./images/test_fig1.png [--theme my_theme.yaml] [--scale 1.0] [--no-inspect]

Creates (next to the image):
    images/test_fig1_drawio_work/
        config.json     source/out/theme/scale paths (read by build.py and iterate.py)
        theme.yaml      copy of --theme (or the skill default) — edit roles/fonts here
        build.py        the build script you edit (from assets/build_template_image.py)
        NOTES.md        element inventory / plan / decisions (fill it in)
        inspect/        grids, zoom crops, palette, boxes, OCR, summary.md
        iterations/     previews, comparisons, lint reports, .drawio snapshots per iteration
Final output: images/test_fig1.drawio  (same path, .drawio extension)
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)


def scaffold_layout(work):
    boxes_path = os.path.join(work, "inspect", "source.boxes.json")
    ocr_path = os.path.join(work, "inspect", "source.ocr.json")
    if not os.path.exists(boxes_path):
        return ""
    try:
        boxes_data = json.load(open(boxes_path, encoding="utf-8"))
        comps = boxes_data.get("components", [])
    except Exception:
        return ""
    ocr_items = []
    if os.path.exists(ocr_path):
        try:
            ocr_items = json.load(open(ocr_path, encoding="utf-8"))
        except Exception:
            pass

    valid = [c for c in comps if c.get("kind") in ("filled box", "outline/frame", "mark/shape") and c["w"] >= 24 and c["h"] >= 16]
    if not valid:
        return ""

    valid.sort(key=lambda c: -c["w"] * c["h"])
    lines = [
        "    # ------------------------------------------------------------------ DETECTED COMPONENTS (Auto-scaffolded)",
        "    # Initial layout anchors detected from source inspection (coordinates in source px).",
        "    # Review/refine against inspect/source.boxes.png and inspect/source.grid*.png:",
    ]

    for c in valid[:35]:
        cid = c["id"]
        x0, y0, x1, y1 = c["bbox"]
        w, h = c["w"], c["h"]
        matched_text = []
        for o in ocr_items:
            ox0, oy0, ox1, oy1 = o["bbox"]
            cx, cy = (ox0 + ox1) / 2, (oy0 + oy1) / 2
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                matched_text.append(o["text"])
        label = "\\n".join(matched_text).replace('"', '\\"') if matched_text else ""
        fill = "background"  # scaffold uses only built-in roles (was: undefined panel_bg)
        stroke = "neutral" if w * h > 30000 else "primary"
        role_label = f'"{label}"' if label else '""'
        lines.append(f'    d.rect({x0}, {y0}, {w}, {h}, label={role_label}, fill="{fill}", stroke="{stroke}", id="comp_{cid}")')

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--theme", help="YAML/TOML/JSON theme to start from (default: assets/theme_image.yaml)")
    ap.add_argument("--scale", type=float, default=1.0, help="output scale vs source px (1.0 = same size)")
    ap.add_argument("--workdir", help="override work dir location")
    ap.add_argument("--force", action="store_true", help="overwrite an existing build.py")
    ap.add_argument("--no-inspect", action="store_true")
    a = ap.parse_args()

    image = os.path.abspath(a.image)
    if not os.path.exists(image):
        sys.exit(f"image not found: {image}")
    stem = os.path.splitext(image)[0]
    out = stem + ".drawio"
    work = os.path.abspath(a.workdir or stem + "_drawio_work")
    for sub in ("", "inspect", "iterations", "crops", "scratch"):
        os.makedirs(os.path.join(work, sub), exist_ok=True)

    theme_src = a.theme or os.path.join(SKILL, "assets", "theme_image.yaml")
    theme_dst = os.path.join(work, "theme" + os.path.splitext(theme_src)[1])
    if not os.path.exists(theme_dst) or a.theme:
        shutil.copy(theme_src, theme_dst)

    cfg = dict(source=image, out=out, theme=theme_dst, scale=a.scale, scripts=HERE, workdir=work)
    json.dump(cfg, open(os.path.join(work, "config.json"), "w", encoding="utf-8"), indent=1)

    if not a.no_inspect:
        subprocess.run([sys.executable, os.path.join(HERE, "inspect_image.py"), "all", image,
                        "--out-dir", os.path.join(work, "inspect"), "--theme", theme_dst], check=False)

    build = os.path.join(work, "build.py")
    if not os.path.exists(build) or a.force:
        t = open(os.path.join(SKILL, "assets", "build_template_image.py"), encoding="utf-8").read()
        scaffold = scaffold_layout(work)
        if scaffold:
            example_marker = "    # Examples (delete when you start):"
            if example_marker in t:
                parts = t.split(example_marker)
                # Keep up to the example marker, insert scaffold, then skip down to 'return d'
                tail = parts[1].split("    return d")[-1]
                t = parts[0] + scaffold + "\n\n    return d" + tail
        t = (t.replace("__IMAGE_NAME__", os.path.basename(image)).replace("__OUT_NAME__", os.path.basename(out))
              .replace("__SCRIPTS__", HERE).replace("__WORKDIR__", work))
        open(build, "w", encoding="utf-8").write(t)
    notes = os.path.join(work, "NOTES.md")
    if not os.path.exists(notes):
        open(notes, "w", encoding="utf-8").write(
            f"# Conversion notes: {os.path.basename(image)}\n\n"
            "## Complexity tier\n(1 simple boxes | 2 tile grid/dashboard | 3 plot/geometric | 4 complex/3-D/photos)\n\n"
            "## Theme mapping (source color -> role)\n\n"
            "## Font sizes (measured px -> size role)\n\n"
            "## Element inventory (region by region, z-order)\n- [ ] \n\n"
            "## Native vs embedded decisions\n\n"
            "## Iteration log\n")
    print(f"\nwork dir : {work}\nbuild    : {build}\ntheme    : {theme_dst}\noutput   : {out}")
    print(f"next     : read {os.path.join(work, 'inspect', 'summary.md')}, view the grid images, fill NOTES.md,\n"
          f"           edit build.py, then: python {os.path.join(HERE, 'iterate.py')} {work} --note 'first pass'")


if __name__ == "__main__":
    main()
