#!/usr/bin/env python3
"""
new_figures.py — set up output folders for turning prose into three figure prototypes per passage.

    python new_figures.py ./drafts/methods.md                     # -> ./drafts/methods_figures/
    python new_figures.py --text "We propose ..." [--name rag]    # -> ./figures/<name or slug>/
    python new_figures.py paper.tex --split --passages 2,4        # several passages -> subfolders
    python new_figures.py notes.md --out-dir ./paper/figs --theme my_theme.yaml

Output location rules (the user can always override with --out-dir):
    input file  <dir>/<stem>.<ext>   ->  <dir>/<stem>_figures/
    pasted text                      ->  ./figures/<name or slug-of-first-words>/
    one passage   -> files directly in that folder
    several       -> one subfolder per passage: p1_<slug>/, p2_<slug>/, ...

Each passage folder gets:
    passage.md      the exact source text (the only allowed source of figure content)
    NOTES.md        claims inventory + chosen figure families (fill in before building)
    build.py        v1 / v2 / v3 builders (from assets/build_template_text.py, families pre-filled)
    _work/          config.json, analysis, iteration snapshots, lint/faithfulness reports
and the output root gets theme.yaml (shared by all passages) and index.md.
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from analyze_text import analyze, read_input, slugify, to_markdown  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", help=".md .txt .tex (.docx/.pdf with optional libs)")
    ap.add_argument("--text", help="inline text instead of a file ('-' = stdin)")
    ap.add_argument("--name", help="folder name for pasted text (default: slug of the first words)")
    ap.add_argument("--out-dir", help="explicit output folder (overrides the defaults)")
    ap.add_argument("--theme", help="theme file to copy (default: assets/theme.yaml); kept if already present")
    ap.add_argument("--split", action="store_true", help="one passage per paragraph/section")
    ap.add_argument("--whole", action="store_true", help="treat the whole input as one passage")
    ap.add_argument("--passages", default="all", help="'all' or comma list of passage numbers, e.g. 1,3")
    ap.add_argument("--min-words", type=int, default=40)
    ap.add_argument("--force", action="store_true", help="overwrite existing build.py / NOTES.md")
    a = ap.parse_args()

    if a.text == "-":
        a.text = sys.stdin.read()
    if not a.path and a.text is None:
        sys.exit("give a file path or --text")
    text = read_input(a.path, a.text)
    passages = analyze(text, True if a.split else False if a.whole else None, a.min_words)
    if a.passages != "all":
        keep = {int(x) for x in a.passages.split(",")}
        passages = [p for p in passages if p["index"] in keep]
    if not passages:
        sys.exit("no passages selected (try --whole or a lower --min-words)")

    if a.out_dir:
        root = os.path.abspath(a.out_dir)
    elif a.path:
        stem = os.path.splitext(os.path.abspath(a.path))[0]
        root = stem + "_figures"
    else:
        root = os.path.abspath(os.path.join("figures", a.name or slugify(text, 5)))
    os.makedirs(root, exist_ok=True)

    theme_dst = os.path.join(root, "theme" + os.path.splitext(a.theme or "x.yaml")[1])
    if a.theme or not os.path.exists(theme_dst):
        shutil.copy(a.theme or os.path.join(SKILL, "assets", "theme.yaml"), theme_dst)

    template = open(os.path.join(SKILL, "assets", "build_template_text.py"), encoding="utf-8").read()
    index = [f"# Figure prototypes", "", f"source: `{a.path or '(pasted text)'}`  ", f"theme: `{theme_dst}`", ""]
    flat = len(passages) == 1
    for p in passages:
        pdir = root if flat else os.path.join(root, f"p{p['index']}_{p['slug']}")
        work = os.path.join(pdir, "_work")
        os.makedirs(work, exist_ok=True)
        open(os.path.join(pdir, "passage.md"), "w", encoding="utf-8").write((f"# {p['heading']}\n\n" if p["heading"] else "") + p["text"] + "\n")
        fams = [f for f, _ in p["suggestions"]] + ["figure"] * 3
        cfg = dict(scripts=HERE, theme=theme_dst, passage=os.path.join(pdir, "passage.md"), passage_dir=pdir,
                   suggestions=p["suggestions"], preview_scale=1.5)
        json.dump(cfg, open(os.path.join(work, "config.json"), "w", encoding="utf-8"), indent=1)
        json.dump({k: v for k, v in p.items() if k != "text"}, open(os.path.join(work, "analysis.json"), "w", encoding="utf-8"), indent=1)
        b = os.path.join(pdir, "build.py")
        if a.force or not os.path.exists(b):
            t = (template.replace("__TITLE__", p["heading"] or p["slug"]).replace("__SCRIPTS__", HERE)
                 .replace("__PASSAGE_DIR__", pdir).replace("__FAMILY1__", fams[0]).replace("__FAMILY2__", fams[1])
                 .replace("__FAMILY3__", fams[2]))
            open(b, "w", encoding="utf-8").write(t)
        n = os.path.join(pdir, "NOTES.md")
        if a.force or not os.path.exists(n):
            eqs = "\n".join(f"- `{e}`" for e in p["display_equations"]) or "- (none)"
            open(n, "w", encoding="utf-8").write(
                f"# Notes — {p['heading'] or p['slug']}\n\n"
                "## Claims inventory (every figure label must trace to one of these)\n"
                "| # | element (entity / step / relation / quantity / conclusion) | quote from passage |\n|---|---|---|\n| 1 | | |\n\n"
                f"## Equations\n{eqs}\n\n"
                "## Prototype plan (three DIFFERENT figure families)\n"
                + "".join(f"- v{i + 1}: **{f}** — {why}\n" for i, (f, why) in enumerate(p["suggestions"]))
                + "\n## Inferred / added content (must also be listed in build.py INFERRED)\n- \n\n## Iteration log\n")
        index.append(f"- **{os.path.relpath(pdir, root) if not flat else '.'}** — {p['words']} words; suggested: "
                     + ", ".join(f for f, _ in p["suggestions"]))
    open(os.path.join(root, "index.md"), "w", encoding="utf-8").write("\n".join(index) + "\n\n" + to_markdown(passages))
    print(to_markdown(passages))
    print(f"output root : {root}\ntheme       : {theme_dst}")
    for p in passages:
        pdir = root if flat else os.path.join(root, f"p{p['index']}_{p['slug']}")
        print(f"passage {p['index']:>2}  : {pdir}")
    print(f"next        : fill NOTES.md, write v1-v3 in build.py, then python {os.path.join(HERE, 'prototype.py')} <passage dir>")


if __name__ == "__main__":
    main()
