#!/usr/bin/env python3
"""
rebuild.py — run the edited copy of the original build script and write the enhanced figure.

    python rebuild.py WORK_DIR [--passes all] [--no-check]

WORK_DIR is the <stem>_enhance_work/ folder made by start_enhance.py. It runs build_enhanced.py
with the enhancement theme (work/theme.yaml), writes brief.figure.output (<stem>#ENHANCED.drawio),
optionally runs enhance.py passes on the result, then checks it:
  text origin  -> faithfulness against passage.md (words not in the passage)
  image origin -> compare.py against the source image (only meaningful when fidelity = exact/polish)
and always the academic audit (after_audit.md + after_print_preview.png).
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from audit_drawio import audit, load_yaml, print_preview, write_report  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work"); ap.add_argument("--passes", default="",
                    help="'all' or comma list for enhance.py, e.g. fonts,sizes,align,fit-page=16")
    ap.add_argument("--no-check", action="store_true")
    a = ap.parse_args()
    work = os.path.abspath(a.work)
    ctx = json.load(open(os.path.join(work, "context.json"), encoding="utf-8"))
    brief = load_yaml(os.path.join(work, "brief.yaml"))
    out = brief["figure"]["output"]
    theme = brief.get("style", {}).get("theme") or ctx["theme"]
    build = os.path.join(work, "build_enhanced.py")
    if not os.path.exists(build):
        sys.exit("no build_enhanced.py — this figure uses the edit route (drawio_doc + enhance.py)")
    if ctx["origin"] == "image-to-drawio":
        cfgp = os.path.join(work, "config.json")
        cfg = json.load(open(cfgp, encoding="utf-8")); cfg.update(out=out, theme=theme, scripts=HERE)
        json.dump(cfg, open(cfgp, "w", encoding="utf-8"), indent=1)
        r = subprocess.run([sys.executable, build], capture_output=True, text=True)
        print(r.stdout.strip()); 
        if r.returncode:
            print(r.stderr); sys.exit("build_enhanced.py failed")
    else:
        from drawio_kit import Diagram, Theme
        spec = importlib.util.spec_from_file_location("build_enhanced", build)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        key = brief.get("figure", {}).get("variant") or ctx.get("variant_key") or m.VARIANTS[0]["key"]
        v = next(v for v in m.VARIANTS if v["key"] == key)
        size = tuple(brief.get("figure", {}).get("canvas") or v["size"])
        d = Diagram(*size, theme=Theme.load(theme), scale=v.get("scale", 1.0))
        v["build"](d)
        d.save(out)
        globals()["_module"] = m
    # fidelity is measured on the raw rebuild: later passes (fit-page) move content
    if not a.no_check and ctx["origin"] == "image-to-drawio" and ctx.get("source_image") and brief.get("content", {}).get("fidelity", "polish") in ("exact", "polish"):
        from compare import compare
        m = compare(ctx["source_image"], out, os.path.join(work, "compare"), "after", quiet=True)
        print(f"fidelity vs source image: score {m['score']:.3f} (pixel {m['pixel_similarity']:.3f}, edge F1 {m['edge_f1']:.3f})")
    if a.passes:
        flags = []
        for p in (["all"] if a.passes == "all" else a.passes.split(",")):
            k, _, val = p.strip().replace("_", "-").partition("=")
            flags += ["--" + k] + ([val] if val else ["16"] if k == "fit-page" else [])
        subprocess.run([sys.executable, os.path.join(HERE, "enhance.py"), out, "-o", out, "--theme", theme,
                        "--brief", os.path.join(work, "brief.yaml"), "--log", os.path.join(work, "CHANGES.md"),
                        "--update-theme", "--add-roles"] + flags, check=True)
    if a.no_check:
        return
    if ctx["origin"] == "text-to-drawio" and ctx.get("source_text") and os.path.exists(ctx["source_text"]):
        from faithful import faithfulness
        allowed = getattr(globals().get("_module"), "ALLOWED_TERMS", []) + list(brief.get("content", {}).get("allowed_terms", []) or [])
        miss = faithfulness(out, open(ctx["source_text"], encoding="utf-8").read(), allowed)
        print("NOT IN SOURCE TEXT:", ", ".join(sorted(miss)) or "none")
    accepted = list((brief.get("review") or {}).get("accepted_warnings", []) or []) + list(getattr(globals().get("_module"), "LINT_IGNORE", []))
    r = audit(out, brief.get("target"), theme, accepted, reference=ctx["figure"])
    write_report(r, work, "after")
    print_preview(out, work, "after", r["brief"]["width_in"])
    print(f"audit after: {r['score']}/100 ({r['n_issues']} issues) -> {os.path.join(work, 'after_audit.md')}")


if __name__ == "__main__":
    main()
