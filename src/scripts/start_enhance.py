#!/usr/bin/env python3
"""
start_enhance.py — gather everything about a figure and prepare the enhancement work folder.

    python start_enhance.py FIG.drawio [--source-image SRC.png] [--text passage.md]
                            [--artifacts DIR] [--theme THEME.yaml] [--suffix "#ENHANCED"]

Finds associated artifacts automatically:
  image-to-drawio : <stem>_drawio_work/ (config.json, build.py, theme, NOTES.md, inspect/, history)
  text-to-drawio  : the passage folder (passage.md, build.py with VARIANTS, CHOSEN.md, prototypes.md,
                    _work/config.json, theme.yaml in the output root)
Creates  <stem>_enhance_work/  next to the figure with:
  context.json / context.md   origin, artifacts, inventory (labels, colors, fonts, sizes, math, rasters),
                              whether the .drawio was hand-edited after it was generated
  brief.yaml                  pre-filled from context; completed from the interview
  questions.md / .json        the interview, filtered to what is still unknown
  before.png, before_audit.md, before_print_preview.png
  theme.yaml                  theme for the enhanced figure (copy of the original or --theme)
  build_enhanced.py (+ config.json)  copy of the original build script when the rebuild route applies
Output figure (later): <stem>#ENHANCED.drawio next to the input.
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from audit_drawio import audit, load_yaml, print_preview, write_report  # noqa: E402
from drawio_doc import Doc  # noqa: E402
from enhance import enhanced_path  # noqa: E402


def find_image_artifacts(fig, explicit=None):
    stem = os.path.splitext(fig)[0]
    cands = [explicit] if explicit else [stem + "_drawio_work"]
    for d in cands:
        if d and os.path.exists(os.path.join(d, "config.json")):
            cfg = json.load(open(os.path.join(d, "config.json"), encoding="utf-8"))
            if "source" in cfg:
                return dict(dir=d, cfg=cfg, build=os.path.join(d, "build.py"), notes=os.path.join(d, "NOTES.md"))
    return None


def find_text_artifacts(fig, explicit=None):
    d = explicit or os.path.dirname(fig)
    if not os.path.exists(os.path.join(d, "passage.md")):
        return None
    cfgp = os.path.join(d, "_work", "config.json")
    cfg = json.load(open(cfgp, encoding="utf-8")) if os.path.exists(cfgp) else {}
    key = None
    m = re.match(r"(v\d+)_", os.path.basename(fig))
    if m:
        key = m.group(1)
    chosen = os.path.join(d, "CHOSEN.md")
    if not key and os.path.exists(chosen):
        m = re.search(r"prototype: `(v\d+)_", open(chosen, encoding="utf-8").read())
        key = m.group(1) if m else None
    theme = cfg.get("theme")
    if not theme or not os.path.exists(theme):
        ups = [d, os.path.dirname(d), os.path.dirname(os.path.dirname(d))]
        cands = [os.path.join(u, n) for u in ups for n in ("theme.yaml", "theme.yml", "theme.toml", "theme.json")]
        if cfg.get("scripts"):
            cands.append(os.path.join(os.path.dirname(cfg["scripts"]), "assets", "theme.yaml"))
        cands.append(os.path.join(SKILL, "assets", "theme.yaml"))   # same defaults as text-to-drawio
        theme = next((t for t in cands if os.path.exists(t)), None)
    return dict(dir=d, cfg=cfg, key=key, build=os.path.join(d, "build.py"), passage=os.path.join(d, "passage.md"),
                theme=theme, chosen=chosen if os.path.exists(chosen) else None)


def load_build_module(path, scripts_dir):
    sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("orig_build_" + str(abs(hash(path))), path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def signature(path):
    doc = Doc.load(path)
    sig = set()
    for c in doc.vertices():
        g = c.abs_geo() or [0, 0, 0, 0]
        sig.add((c.plain[:40], round(g[0]), round(g[1]), round(g[2]), round(g[3]), c.get("fillColor", "")))
    return sig


def rebuild_original(origin, art, tmp):
    """Re-run the original build to a temp file (to detect hand edits). Returns path or None."""
    try:
        if origin == "image-to-drawio":
            cfg = dict(art["cfg"]); out = os.path.join(tmp, "orig.drawio"); cfg["out"] = out
            wd = os.path.join(tmp, "imgwork"); os.makedirs(wd, exist_ok=True)
            shutil.copy(art["build"], os.path.join(wd, "build.py"))
            json.dump(cfg, open(os.path.join(wd, "config.json"), "w", encoding="utf-8"))
            subprocess.run([sys.executable, os.path.join(wd, "build.py")], check=True, capture_output=True, timeout=300)
            return out
        if origin == "text-to-drawio" and art.get("key"):
            from drawio_kit import Diagram, Theme
            m = load_build_module(art["build"], art["cfg"].get("scripts", HERE))
            v = next(v for v in m.VARIANTS if v["key"] == art["key"])
            d = Diagram(*v["size"], theme=Theme.load(art["theme"]), scale=v.get("scale", 1.0))
            v["build"](d)
            out = os.path.join(tmp, "orig.drawio"); d.save(out, quiet=True)
            return out
    except Exception as e:
        print("  (could not rebuild the original for comparison:", str(e).splitlines()[-1] if str(e) else e, ")")
    return None


def inventory(doc):
    v = doc.vertices()
    labels = [c for c in v if c.plain]
    sizes, fams, colors = {}, {}, {}
    for c in labels:
        sizes[c.get("fontSize", "11")] = sizes.get(c.get("fontSize", "11"), 0) + 1
        if not c.is_math:
            fams[c.get("fontFamily", "Helvetica")] = fams.get(c.get("fontFamily", "Helvetica"), 0) + 1
    for c in doc.cells:
        for k in ("fillColor", "strokeColor", "fontColor"):
            x = c.get(k)
            if x and x.startswith("#"):
                colors[x.lower()] = colors.get(x.lower(), 0) + 1
    rasters = [c.id for c in v if c.is_image and re.match(r"data:image/(png|jpe?g|webp)", c.get("image", ""))]
    svgs = [c.id for c in v if c.is_image and "svg+xml" in c.get("image", "")]
    maths = [c.plain for c in v if c.is_math]
    uni = [c.plain for c in labels if not c.is_math and re.search("[λθαβγδσμπΣΔ∑∫≤≥×∈]", c.plain)]
    panels = [c.plain for c in labels if re.match(r"^\(?[a-dA-D1-4][\).]\s", c.plain)]
    pw = doc.page[0]
    emph = sorted((c for c in v if c.plain and not c.is_text and c.abs_geo() and c.abs_geo()[2] < 0.35 * pw
                   and c.get("fillColor", "").lower() not in ("", "none", "#ffffff")),
                  key=lambda c: (-float(c.get("fontStyle", 0) == "1" or "<b>" in c.value), -float(c.get("fontSize", 11))))
    cand = []
    for c in emph + [c for c in labels if c not in emph]:
        t = c.plain.replace("\n", " ")
        if 2 < len(t) <= 40 and t not in cand and not c.is_math:
            cand.append(t)
        if len(cand) >= 3:
            break
    return dict(vertices=len(v), edges=len(doc.edges()), groups=sum(c.is_group for c in doc.cells), labels=len(labels),
                label_texts=[c.plain for c in labels][:80], font_sizes=sizes, font_families=fams, colors=colors,
                raster_images=rasters, svg_layers=svgs, math_labels=maths, unicode_math_labels=uni, panel_labels=panels,
                candidate_emphasis=cand + ["Nothing in particular"], page=list(doc.page), math_flag=doc.math)


def applies(q, ctx):
    a = q.get("applies", "always")
    return {"always": True, "image": ctx["origin"] == "image-to-drawio", "text": ctx["origin"] == "text-to-drawio",
            "math": bool(ctx["inventory"]["math_labels"] or ctx["inventory"]["unicode_math_labels"]),
            "photos": bool(ctx["inventory"]["raster_images"]), "inferred": bool(ctx.get("inferred")),
            "multi_panel": bool(ctx["inventory"]["panel_labels"])}.get(a, True)


def set_key(d, dotted, value):
    ks = dotted.split(".")
    for k in ks[:-1]:
        d = d.setdefault(k, {})
    d[ks[-1]] = value


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("drawio"); ap.add_argument("--source-image"); ap.add_argument("--text")
    ap.add_argument("--artifacts", help="work dir of image-to-drawio or passage dir of text-to-drawio")
    ap.add_argument("--theme", help="theme for the enhanced figure (default: the original's theme)")
    ap.add_argument("--suffix", default="#ENHANCED"); ap.add_argument("--work-dir")
    a = ap.parse_args()

    import yaml
    fig = os.path.abspath(a.drawio)
    stem = os.path.splitext(fig)[0]
    name = os.path.basename(stem)
    out = enhanced_path(fig, a.suffix)
    work = os.path.abspath(a.work_dir or stem + "_enhance_work")
    os.makedirs(work, exist_ok=True)

    img = find_image_artifacts(fig, a.artifacts)
    txt = None if img else find_text_artifacts(fig, a.artifacts)
    origin = "image-to-drawio" if img else "text-to-drawio" if txt else ("image-to-drawio" if a.source_image else
                                                                         "text-to-drawio" if a.text else "unknown")
    art = img or txt or {}
    source_image = a.source_image or (img["cfg"]["source"] if img else "")
    source_text = a.text or (txt["passage"] if txt else "")
    theme_src = a.theme or (img and img["cfg"].get("theme")) or (txt and txt.get("theme")) or \
        os.path.join(SKILL, "assets", "themes", "navy_default.yaml")
    theme_dst = os.path.join(work, "theme.yaml")          # always YAML so brief.py can edit it
    if not os.path.exists(theme_dst) or a.theme:
        from drawio_kit import Theme
        yaml.safe_dump(Theme.load(theme_src).to_dict(), open(theme_dst, "w", encoding="utf-8"), sort_keys=False, allow_unicode=True)

    doc = Doc.load(fig)
    inv = inventory(doc)
    inferred, caption = [], ""
    build_path = art.get("build") if art and os.path.exists(art.get("build", "")) else ""
    if txt and build_path:
        try:
            m = load_build_module(build_path, txt["cfg"].get("scripts", HERE))
            inferred = [x for x in getattr(m, "INFERRED", []) if not txt.get("key") or not re.match(r"v\d+:", x) or x.startswith(txt["key"] + ":")]
            v = next((v for v in m.VARIANTS if v["key"] == txt.get("key")), None)
            caption = (v or {}).get("caption", "")
        except Exception as e:
            print("  (could not read build.py:", e, ")")

    edited, diff = None, None
    if build_path:
        with tempfile.TemporaryDirectory() as tmp:
            orig = rebuild_original(origin, art, tmp)
            if orig:
                s1, s2 = signature(orig), signature(fig)
                diff = len(s1 ^ s2)
                edited = diff > 0
    route = "rebuild" if build_path and edited is False else "edit"

    ctx = dict(figure=fig, name=name, output=out, origin=origin, work_dir=work, artifacts=art.get("dir", ""),
               source_image=source_image, source_text=source_text, build_script=build_path, variant_key=art.get("key"),
               theme=theme_dst, original_theme=theme_src, edited_after_build=edited, signature_diff=diff,
               recommended_route=route, inferred=inferred, draft_caption=caption, inventory=inv)
    json.dump(ctx, open(os.path.join(work, "context.json"), "w", encoding="utf-8"), indent=1, default=str)

    # brief
    brief = load_yaml(os.path.join(SKILL, "assets", "brief_template.yaml"))
    bp = os.path.join(work, "brief.yaml")
    if os.path.exists(bp):
        brief = load_yaml(bp)
    for k, v in {"figure.name": name, "figure.input": fig, "figure.origin": origin, "figure.source_image": source_image,
                 "figure.source_text": source_text, "figure.build_script": build_path, "figure.output": out,
                 "style.theme": theme_dst, "plan.route": route}.items():
        set_key(brief, k, v)
    if caption and not brief.get("content", {}).get("caption"):
        set_key(brief, "content.caption", caption)
    yaml.safe_dump(brief, open(bp, "w", encoding="utf-8"), sort_keys=False, allow_unicode=True)

    # rebuild route setup
    if build_path:
        dst = os.path.join(work, "build_enhanced.py")
        if not os.path.exists(dst):
            shutil.copy(build_path, dst)
        if origin == "image-to-drawio":
            cfg = dict(img["cfg"]); cfg.update(out=out, theme=theme_dst, scripts=HERE, workdir=work)
            json.dump(cfg, open(os.path.join(work, "config.json"), "w", encoding="utf-8"), indent=1)

    # before: preview + audit
    from render_preview import render_kit
    render_kit(fig, os.path.join(work, "before.png"), scale=1.5)
    r = audit(fig, brief.get("target"), theme_dst)
    write_report(r, work, "before")
    print_preview(fig, work, "before", r["brief"]["width_in"])

    # questions
    bank = load_yaml(os.path.join(SKILL, "assets", "questions.yaml"))
    qs_out, md = [], [f"# Interview for `{name}`", "",
                      "Ask round by round (<= 3-4 questions per message, options as buttons when possible). "
                      "Write answers into brief.yaml at the given key. Skip a question if the user already answered it.", ""]
    for rnd in bank["rounds"]:
        items = [q for q in rnd["questions"] if applies(q, ctx)]
        if not items:
            continue
        md += [f"## {rnd['name']}", ""]
        for q in items:
            opts = inv.get(q["options_from"], []) if q.get("options_from") else q.get("options", [])
            extra = ""
            if q["id"] == "inferred":
                extra = "\n  - inferred items: " + "; ".join(inferred)
            if q["id"] == "caption" and caption:
                extra = f"\n  - draft caption: {caption}"
            md.append(f"- **{q['ask']}**  → `{q['brief_key']}`" + (f"\n  - options: {' | '.join(map(str, opts))}" if opts else "\n  - (free text)") + extra)
            qs_out.append(dict(round=rnd["name"], id=q["id"], ask=q["ask"], options=opts, key=q["brief_key"]))
        md.append("")
    open(os.path.join(work, "questions.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(qs_out, open(os.path.join(work, "questions.json"), "w", encoding="utf-8"), indent=1)

    cm = [f"# Enhancement context: `{name}`", "",
          f"- origin: **{origin}**; artifacts: `{art.get('dir', '—')}`",
          f"- source image: `{source_image or '—'}`; source text: `{source_text or '—'}`",
          f"- build script: `{build_path or '—'}`" + (f" (variant {art.get('key')})" if art.get("key") else ""),
          f"- hand-edited after generation: {edited if edited is not None else 'unknown'}"
          + (f" ({diff} differing elements)" if diff else ""),
          f"- recommended route: **{route}** — " + ("re-run an edited copy of the build script (build_enhanced.py), then enhance.py"
                                                    if route == "rebuild" else "edit the .drawio directly (drawio_doc API + enhance.py)"),
          f"- theme for enhancement: `{theme_dst}`",
          f"- output: `{out}`", "",
          f"## Inventory", "",
          f"- {inv['vertices']} vertices, {inv['edges']} edges, {inv['groups']} groups, {inv['labels']} labels; page {inv['page']}",
          f"- font families {inv['font_families']}; sizes {inv['font_sizes']}",
          f"- colors {inv['colors']}",
          f"- math labels: {len(inv['math_labels'])} (flag {'on' if inv['math_flag'] else 'off'}); Unicode-math labels: {len(inv['unicode_math_labels'])}",
          f"- raster images: {len(inv['raster_images'])}; SVG layers: {len(inv['svg_layers'])}; panel labels: {inv['panel_labels'] or '—'}",
          f"- inferred content (text origin): {inferred or '—'}", f"- draft caption: {caption or '—'}", "",
          f"## Before", "", f"- audit score **{r['score']}/100** ({r['n_issues']} issues) — see before_audit.md",
          "- previews: before.png, before_print_preview.png (actual print size)"]
    open(os.path.join(work, "context.md"), "w", encoding="utf-8").write("\n".join(cm) + "\n")
    print("\n".join(cm))
    print(f"\nnext: interview the user with {os.path.join(work, 'questions.md')}, fill brief.yaml, then follow SKILL.md (enhance mode, C4)")


if __name__ == "__main__":
    main()
