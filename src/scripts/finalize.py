#!/usr/bin/env python3
"""
finalize.py — keep the prototype the user picked.

    python finalize.py PASSAGE_DIR --pick v2 [--name rag_pipeline] [--clean]

Copies <pick>_<style>.drawio/.png to <name>.drawio/.png in the same folder (default name: the
passage folder name, or "figure" for a flat folder named *_figures), writes CHOSEN.md with the
draft caption and inferred-content list, and with --clean deletes the other prototypes'
.drawio/.png files (the _work/ snapshots are kept for regeneration).
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import glob
import importlib.util
import os
import re
import shutil
import sys

sys.dont_write_bytecode = True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("passage_dir"); ap.add_argument("--pick", required=True)
    ap.add_argument("--name"); ap.add_argument("--clean", action="store_true")
    a = ap.parse_args()
    pdir = os.path.abspath(a.passage_dir)
    src = sorted(glob.glob(os.path.join(pdir, f"{a.pick}_*.drawio")))
    if not src:
        raise SystemExit(f"no {a.pick}_*.drawio in {pdir} (run prototype.py first)")
    folder = os.path.basename(pdir)
    name = a.name or re.sub(r"^p\d+_", "", folder.replace("_figures", "")) or "figure"
    dst = os.path.join(pdir, name + ".drawio")
    shutil.copy(src[0], dst)
    png = src[0][:-7] + ".png"
    if os.path.exists(png):
        shutil.copy(png, dst[:-7] + ".png")
    caption, inferred = "", []
    bp = os.path.join(pdir, "build.py")
    if os.path.exists(bp):
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            spec = importlib.util.spec_from_file_location("b", bp); m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            v = next((v for v in m.VARIANTS if v["key"] == a.pick), {})
            caption = v.get("caption", "")
            inferred = [x for x in getattr(m, "INFERRED", []) if x.lower().startswith(a.pick + ":") or ":" not in x[:4]]
        except Exception:
            pass
    open(os.path.join(pdir, "CHOSEN.md"), "w", encoding="utf-8").write(
        f"# Chosen figure\n\n- prototype: `{os.path.basename(src[0])}`\n- final: `{os.path.basename(dst)}`\n"
        f"- draft caption: {caption or '—'}\n- inferred content: {'; '.join(inferred) or 'none'}\n")
    if a.clean:
        for f in glob.glob(os.path.join(pdir, "v[0-9]_*.drawio")) + glob.glob(os.path.join(pdir, "v[0-9]_*.png")):
            os.remove(f)
    print("final:", dst)


if __name__ == "__main__":
    main()
