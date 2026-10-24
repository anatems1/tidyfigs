#!/usr/bin/env python3
"""
report.py — final before/after report and exports for an enhanced figure.

    python report.py WORK_DIR [--export pdf,svg,png] [--dpi 300]

Writes WORK_DIR/before_after.png (screen previews + actual-print-size previews, with audit scores),
WORK_DIR/REPORT.md (brief summary, audit table before/after, CHANGES.md, remaining issues), and
exports next to the figure. Export names replace '#' with '_' (LaTeX \\includegraphics and URLs
break on '#'): <stem>_ENHANCED.pdf / .svg / .png. Vector export needs the draw.io desktop CLI;
without it a high-resolution PNG is rendered with the built-in previewer (no MathJax / no vector).
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
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from audit_drawio import audit, load_yaml, print_preview, write_report  # noqa: E402


def drawio_cli():
    exe = shutil.which("drawio") or shutil.which("draw.io")
    if not exe and sys.platform.startswith("win"):
        cand = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "draw.io", "draw.io.exe")
        if os.path.exists(cand):
            exe = cand
    return exe


def export(src, dst, fmt, scale=1.0):
    exe = drawio_cli()
    if not exe:
        return False
    cmd = [exe, "--export", "--format", fmt, "--crop", "--output", dst, src, "--no-sandbox"]
    if fmt == "png":
        cmd[4:4] = ["--scale", str(scale)]
    if fmt == "svg":
        cmd.insert(4, "--embed-svg-images")
    if not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
        cmd = ["xvfb-run", "-a"] + cmd
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=240)
        return os.path.exists(dst)
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work"); ap.add_argument("--export", default="pdf,svg,png"); ap.add_argument("--dpi", type=int, default=300)
    a = ap.parse_args()
    work = os.path.abspath(a.work)
    ctx = json.load(open(os.path.join(work, "context.json"), encoding="utf-8"))
    brief = load_yaml(os.path.join(work, "brief.yaml"))
    out = brief["figure"]["output"]
    theme = brief.get("style", {}).get("theme") or ctx["theme"]
    from render_preview import render_kit
    render_kit(out, os.path.join(work, "after.png"), scale=1.5)
    accepted = (brief.get("review") or {}).get("accepted_warnings", []) or []
    rb = audit(ctx["figure"], brief.get("target"), theme)
    ra = audit(out, brief.get("target"), theme, accepted, reference=ctx["figure"])
    write_report(rb, work, "before"); write_report(ra, work, "after")
    w_in = ra["brief"]["width_in"]
    print_preview(ctx["figure"], work, "before", w_in); print_preview(out, work, "after", w_in)

    from PIL import Image, ImageDraw, ImageFont
    from drawio_kit import find_font_file
    B = ImageFont.truetype(find_font_file("Helvetica", bold=True), 26); R = ImageFont.truetype(find_font_file("Helvetica"), 20)
    ims = [Image.open(os.path.join(work, p)).convert("RGB") for p in ("before.png", "after.png", "before_print_preview.png", "after_print_preview.png")]
    colw = 900
    big = [im.resize((colw, int(im.height * colw / im.width))) for im in ims[:2]]
    small = [im if im.width <= colw else im.resize((colw, int(im.height * colw / im.width))) for im in ims[2:]]
    scaled = any(im.width > colw for im in ims[2:])
    H = 70 + max(i.height for i in big) + 90 + max(i.height for i in small) + 40
    W = 60 + 2 * colw + 40
    sheet = Image.new("RGB", (W, H), "#eef1f5"); dr = ImageDraw.Draw(sheet)
    for k, (im, lab, r) in enumerate(zip(big, ("BEFORE", "AFTER  (#ENHANCED)"), (rb, ra))):
        x = 30 + k * (colw + 40)
        dr.text((x, 20), f"{lab} — readiness {r['score']}/100, {r['n_issues']} issues", font=B, fill="#19355d")
        sheet.paste(im, (x, 60)); dr.rectangle([x, 60, x + im.width, 60 + im.height], outline="#a4a4a4", width=2)
    y = 60 + max(i.height for i in big) + 30
    for k, im in enumerate(small):
        x = 30 + k * (colw + 40)
        dr.text((x, y), f"print size {w_in} in at 150 dpi" + (" (scaled to fit this sheet)" if scaled else ""), font=R, fill="#333333")
        sheet.paste(im, (x, y + 34)); dr.rectangle([x, y + 34, x + im.width, y + 34 + im.height], outline="#a4a4a4", width=1)
    sheet.save(os.path.join(work, "before_after.png"))

    exported, notes = [], []
    base = os.path.splitext(out)[0].replace("#", "_")
    for fmt in [f.strip() for f in a.export.split(",") if f.strip()]:
        dst = f"{base}.{fmt}"
        if export(out, dst, fmt, scale=a.dpi / 96):
            exported.append(dst)
        elif fmt == "png":
            render_kit(out, dst, width=int(w_in * a.dpi), dpi=a.dpi)
            exported.append(dst); notes.append("PNG rendered with the built-in previewer (approximate; math via matplotlib)")
        else:
            notes.append(f"{fmt.upper()} needs the draw.io desktop CLI (not found) — export from draw.io: File > Export as > {fmt.upper()}")
    changes = open(os.path.join(work, "CHANGES.md"), encoding="utf-8").read() if os.path.exists(os.path.join(work, "CHANGES.md")) else "(none logged)"
    md = [f"# Enhancement report: `{os.path.basename(out)}`", "",
          f"- input: `{ctx['figure']}` ({ctx['origin']})", f"- output: `{out}`",
          f"- target: {brief.get('target', {}).get('venue', '?')} / {w_in} in / min {ra['brief']['min_font_pt']} pt / "
          f"print {brief.get('target', {}).get('print_mode', '?')} / colorblind {brief.get('target', {}).get('colorblind')}",
          f"- purpose: {brief.get('intent', {}).get('purpose', '')} — takeaway: {brief.get('intent', {}).get('takeaway', '')}",
          f"- caption: {brief.get('content', {}).get('caption', '') or '—'}", "",
          "| area | before | after |", "|---|---|---|"]
    for k in ra["issues"]:
        md.append(f"| {k} | {len(rb['issues'][k])} | {len(ra['issues'][k])} |")
    md += [f"| **score** | **{rb['score']}** | **{ra['score']}** |", "", "![before/after](before_after.png)", "",
           "## Changes", "", changes, "", "## Remaining issues", ""]
    md += [f"- [{k}] {x}" for k, v in ra["issues"].items() for x in v] or ["- none"]
    md += ["", "## Exports", ""] + [f"- `{p}`" for p in exported] + [f"- note: {n}" for n in notes]
    open(os.path.join(work, "REPORT.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print(f"before {rb['score']} -> after {ra['score']}; wrote {os.path.join(work, 'REPORT.md')} and before_after.png")
    for p in exported:
        print("exported", p)
    for n in notes:
        print("note:", n)


if __name__ == "__main__":
    main()
