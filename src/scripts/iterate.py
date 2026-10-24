#!/usr/bin/env python3
"""
iterate.py — one build/verify cycle: run build.py -> render preview -> compare -> lint -> log.

    python iterate.py WORKDIR [--note "moved header text up 4px"] [--no-snapshot]

Outputs in WORKDIR/iterations/:
    iter_NN.drawio            snapshot of the output (roll back by copying it to the output path)
    iter_NN_preview.png       page-aligned render of the .drawio at source resolution
    iter_NN_side.png          source | preview with a coordinate grid       <- look at this
    iter_NN_edges.png         red = only in source, cyan = only in preview  <- alignment errors
    iter_NN_heat.png          worst cells outlined with their coordinates
    iter_NN_metrics.json, iter_NN_lint.txt
and appends a row to WORKDIR/history.json (printed as a table).
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
from compare import compare  # noqa: E402
from lint_drawio import lint  # noqa: E402
from render_preview import render_kit  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir"); ap.add_argument("--note", default="")
    ap.add_argument("--no-snapshot", action="store_true")
    a = ap.parse_args()
    work = os.path.abspath(a.workdir)
    cfg = json.load(open(os.path.join(work, "config.json")))
    hist_p = os.path.join(work, "history.json")
    hist = json.load(open(hist_p)) if os.path.exists(hist_p) else []
    n = len(hist) + 1
    tag = f"iter_{n:02d}"
    it = os.path.join(work, "iterations"); os.makedirs(it, exist_ok=True)

    r = subprocess.run([sys.executable, os.path.join(work, "build.py")], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr)
        sys.exit("build.py failed — fix the error above (no iteration recorded)")
    if r.stderr.strip():
        print(r.stderr.strip())
    out = cfg["out"]
    if not a.no_snapshot:
        shutil.copy(out, os.path.join(it, f"{tag}.drawio"))
    from PIL import Image
    with Image.open(cfg["source"]) as s:
        sw = s.width
    prev = os.path.join(it, f"{tag}_preview.png")
    render_kit(out, prev, width=sw)
    m = compare(cfg["source"], prev, it, tag, quiet=True)
    L = lint(out, cfg["theme"], cfg.get("scale", 1.0))
    with open(os.path.join(it, f"{tag}_lint.txt"), "w") as fh:
        for k in ("errors", "warnings", "info"):
            for line in L[k]:
                fh.write(f"{k[:-1].upper() if k != 'info' else 'INFO'}  {line}\n")
    hist.append(dict(iter=n, score=m["score"], pixel=m["pixel_similarity"], edge_f1=m["edge_f1"],
                     errors=len(L["errors"]), warnings=len(L["warnings"]), note=a.note))
    json.dump(hist, open(hist_p, "w"), indent=1)

    print(f"\n{'iter':>4} {'score':>6} {'pixel':>6} {'edgeF1':>6} {'err':>4} {'warn':>5}  note")
    for h in hist:
        print(f"{h['iter']:>4} {h['score']:>6.3f} {h['pixel']:>6.3f} {h['edge_f1']:>6.3f} {h['errors']:>4} {h['warnings']:>5}  {h['note']}")
    if len(hist) > 1 and hist[-1]["score"] < hist[-2]["score"] - 0.005:
        print(f"\n!! score dropped vs iter {n - 1}; consider reverting (iterations/iter_{n - 1:02d}.drawio)")
    print("\nworst cells (x0,y0,x1,y1):")
    for c in m["worst_cells"][:6]:
        print(f"  {c['box']}  bad={c['bad']}  missing_edges={c['missing_edges']} extra_edges={c['extra_edges']}")
    for e in L["errors"][:10]:
        print("ERROR", e)
    for w in L["warnings"][:15]:
        print("WARN ", w)
    if len(L["warnings"]) > 15:
        print(f"  ... {len(L['warnings']) - 15} more in {tag}_lint.txt")
    print(f"\nVIEW: {m['images']['side']}\n      {m['images']['edges']}\n      {m['images']['heat']}")


if __name__ == "__main__":
    main()
