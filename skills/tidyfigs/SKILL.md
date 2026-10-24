---
name: tidyfigs
description: >-
  Make EDITABLE, publication-grade draw.io / diagrams.net figures for academic papers, in three
  modes: (A) IMAGE → convert a raster figure (PNG/JPG/WebP diagram, flowchart, infographic,
  conceptual plot, scientific figure) into native draw.io objects; (B) TEXT → turn prose or LaTeX
  equations (methods, framework, comparison, results, equation) into three different figure
  prototypes for the user to pick from; (C) ENHANCE → interview the user, then polish any .drawio
  for a target venue (print size, fonts, color/grayscale, LaTeX, connectors, caption) and export.
  Use for: convert/recreate/vectorize/"make editable" an image as .drawio; make a figure, diagram,
  schematic or visual abstract from text; enhance/polish/finalize a diagram for publication.
license: MIT (see LICENSE in the repository)
compatibility: >-
  Python 3.9+ with numpy, pillow, matplotlib, pyyaml. Optional: scipy/opencv (detection, diffs),
  pytesseract + tesseract (OCR), python-docx / pypdf (.docx/.pdf input), draw.io desktop CLI
  (exact renders, vector PDF/SVG export).
metadata:
  version: "2.0"
  files: SKILL.md (this) · REFERENCE.md (API, rules, catalogs) · EXAMPLES.md · drawio_toolkit.py (all code)
---

# Editable draw.io figures for academic papers

You **build** figures as native draw.io objects from a Python **build script** (the artifact of
record: every coordinate, role and size lives there, so the figure can be regenerated and re-themed).
Never trace pixels, never rasterize text. Details for every call and rule: `REFERENCE.md`.
Patterns to copy: `EXAMPLES.md`.

## Running the tools

All code ships in one file. `T` below means `python drawio_toolkit.py`:
```bash
T <tool> [args]        # e.g. T lint_drawio fig.drawio --theme theme.yaml   (any tool: --help)
T unpack ./tidyfigs        # optional: normal folder scripts/ assets/ examples/; then python scripts/<tool>.py
```
In Python: `import drawio_toolkit; drawio_toolkit.setup()` → `from drawio_kit import Diagram`,
`from figlib import *`, `from drawio_doc import Doc`. Generated build scripts find the library by
themselves.

**No code execution available?** Still follow the same method: write the build script (or, for small
figures, the draw.io XML directly — REFERENCE §14) for the user to run, and ask them for the
preview/lint output or screenshots instead of viewing them yourself.

## Pick the mode

| Input | Mode | Output |
|---|---|---|
| raster image to recreate | **A image** | `<img>.drawio` + `<img>#drawio.png` (300 dpi) next to the image |
| prose / paper section / equation | **B text** | 3 prototypes → user picks → `<name>.drawio` |
| an existing .drawio to make publication-ready | **C enhance** | `<name>#ENHANCED.drawio` + PDF/SVG/PNG exports |

A or B is often followed by C. Ask which mode only if the request is genuinely ambiguous.

## Shared rules (all modes)

- **Theme roles only.** Colors, fonts, sizes, strokes, opacities come from a YAML/TOML/JSON theme
  (`fill="primary"`, `size="body"`, `sw="thick"`, `fill_opacity="tint"`). Tints = existing role +
  opacity role, not new hex. Need a new color? Add a *semantic* role (`highlight`, `chunk_b`) and tell
  the user. Lint reports every off-theme value; finals have none.
- **Regularize to intent**: peers get identical sizes, rows/columns one gap (`row`, `row_widths`,
  `fit_row`, `column`, `grid_boxes`), shared edges one coordinate; center labels on what they label
  (`x + w/2`). Ignore ±1 px noise.
- **Attach connectors** with `src`/`tgt` (+ `exit`/`entry` fractions) whenever a line touches a shape;
  `pts` lists only what draw.io can't compute (free start, waypoints, free end). Free points only for
  dividers, plot axes, unattached vectors.
- **Curved edges** (`route="curved"`, `flex_arrow`, `cycle`): waypoints are *control points*; the
  curve passes through midpoints between consecutive waypoints.
- **Z-order** = creation order (later on top): canvas → panels → fills → shapes → connectors → text
  → annotations. Group things that move together (`with d.group("tile")`).
- **Stable ids** on important vertices (needed for edges, readable lint).
- Text markup: `**bold**` `*italic*` `__underline__` `{role|colored}` `\n` `\*`; inline LaTeX `\( … \)`;
  display math via `d.equation(r"...")` (native MathJax, editable). `raw=True` passes HTML.
- **Verify by looking**: after every build, view the PNG preview(s) with your image tool; the
  numbers (lint, scores, audits) guide, the visual check decides. Preview approximates draw.io:
  emoji = grey squares, cylinders/documents = rectangles, no small caps, math via mathtext.
- **Workspace hygiene**: scratch scripts, probes and crops go in `<workdir>/scratch/`, never next to
  the user's files.
- **Academic defaults**: white background, no in-figure title (draft a caption instead), ≤ 3 hues +
  tints, color never the only encoding, one font family, ≤ 6–7 size roles, ≤ ~25 text items.

---

## Mode A — image → editable draw.io

Method: **measure → plan → theme → build script → render → compare → fix**, until the preview
matches the source in layout. Coordinates are **source-image pixels measured on the real grid**
(eyeballing a resized view is the #1 cause of bad conversions).

**A0 Triage** (sets effort; read the closest example in EXAMPLES.md first):

| Tier | Looks like | Main techniques | Iterations | Final score |
|---|---|---|---|---|
| 1 simple | boxes, labels, straight/elbow arrows, 1–3 panels | `rect`, `text`, attached `edge`, `row` | 2–3 | ≥ 0.88 |
| 2 grid/dashboard | tiles with icons, columns, mini flows, bullets | `panel`, groups, `fit_row`/`grid_boxes`, `icon`, orthogonal edges | 3–5 | ≥ 0.88 |
| 3 plot/geometric | axes, vectors, points, circles, wavy arrows, rotated labels | `dot`, `circle`, anchors, `flex_arrow`, curved edges, `rotation` | 3–6 | ≥ 0.85 |
| 4 complex | 3-D surfaces, meshes, photos, dense scatter, callouts | `surface_mesh`, `polygon`, `image_crop`, `scatter_*`, `callout`, z-layering | 5–10 | ≥ 0.78 |

**A1 Scaffold + inspect**: `T new_build images/fig.png [--theme user.yaml] [--scale 1]` creates
`images/fig_drawio_work/` (build.py, theme.yaml, NOTES.md, inspect/, iterations/, scratch/,
history.json; keep it). Read `inspect/summary.md` and **view** `source.grid*.png` (positions),
`source.boxes.png/.json` (exact bboxes + median colors — use directly), `source.ocr.png/.json` (text +
font size: use the width-fit `est_px_if_regular/bold`, pick by looking), `source.palette.png`
(colors → nearest role, ΔE). The scaffold pre-fills detected boxes in build.py — refine them.
Zoom any region: `T inspect_image zoom SRC --box x0 y0 x1 y1 --factor 3 --step 10`; probe thin/light
features numerically (`T inspect_image probe SRC --box …` or numpy, REFERENCE §6.1). OCR misreads and
the detector merges touching shapes — always check visually.

**A2 Plan in NOTES.md**: inventory region by region in z-order. Decide per element:
native vertex (boxes, panels, pills, circles, diamonds, cylinders) · native text (all text, always) ·
attached `edge` (connections) · free `edge` (axes, dividers) · `flex_arrow` (wide/wavy) · `dot`s in a
group (scatter ≤ ~400) · `polygon`/`svg_layer`/`surface_mesh` (blobs, beams, meshes, 3-D) ·
`image_crop` (photos, textures, logos only — rebuild their labels natively on top) · library shape or
emoji `icon` (icons; say which). Record every non-native decision for the report.

**A3 Theme**: user colors/fonts → roles, map every source color to the nearest role; otherwise the
source's dominant colors deduplicated to ≤ 6–8 roles. Cluster OCR sizes into ≤ 6–7 size roles (same
visual level ⇒ same role). Closest web-safe family (Helvetica/Arial; Times New Roman for LaTeX-style
serif); `google: true` for Roboto/Inter. Measure stroke thickness on a zoom.

**A4 Write build.py** (`Diagram.from_source` is pre-wired; full API REFERENCE §2):
```python
pid, (cx, cy, cw, ch) = d.panel(52, 110, 620, 570, "**AUTO-ENCODING**", header_h=70, header_fill="primary",
                                header_color="background", title_size="heading")
for (x, y, w, h), t in zip(d.row_widths(182, 336, [97, 138, 97, 97], 62, gap=13), ["[A]", "[MASK]", "[C]", "[D]"]):
    d.rect(x, y, w, h, t, fill="token", stroke="text", rounded=4, size="body", id="tok_" + t.strip("[]"))
d.rect(275, 455, 170, 62, "**Encoder**", fill="primary", color="background", rounded=4, id="enc")
d.edge([], src="enc", tgt="tok_MASK", sw="thick", exit=(.5, 0), entry=(.5, 1))
d.edge([(108, 486)], tgt="enc", entry=(0, .5))                     # free start, attached end
d.text("Dimension 2", 365, 144, size="small", rotation=-90)
d.image_crop((49, 199, 143, 309), border="text")                   # photo copied from the source
```
Randomized content (scatter) uses a fixed `seed` and keep-out rects around labels. > ~600 vertices →
merge decorative marks into one `svg_layer`. Tiny sources → `--scale 2` so text ≥ 10 px.

**A5 Iterate**: `T iterate images/fig_drawio_work --note "what changed"` = build → render → compare →
lint → snapshot + history. View `iter_NN_side.png` (everything: wording, sizes, weights, wrapping),
`iter_NN_edges.png` (**red = source only, cyan = preview only**; move until pairs merge),
`iter_NN_heat.png` + worst cells (zoom those next). Work in passes: (1) canvas, panels, grids →
(2) shapes snapped to detected bboxes and regularized → (3) every connector attached with ports →
(4) font roles, weights, centering, `valign` → (5) edge-diff polish. Change a few related things per
iteration; if the score drops, revert. **Stop** when: every inventory element is present (re-read the
source region by region), lint 0 errors and no overflow/overlap/off-theme warnings, side-by-side shows
no misplacement or wrong text, score plateaued (< 0.005 gain over 2 iterations). If the draw.io CLI
exists: one final `T render_preview OUT --engine drawio`.

**A6 Finalize**: `images/fig.drawio` is the latest build; export
`T render_preview images/fig.drawio -o "images/fig#drawio.png" --dpi 300`. The image folder holds only
source, `.drawio`, `#drawio.png` (+ the work dir). Report: paths; native vs embedded (photos, SVG
layers, emoji placeholders); roles used/added; known deviations; source typos kept; how to re-theme
(edit theme.yaml → `python build.py`) and rescale.

---

## Mode B — text → three editable figure prototypes

Read the passage, inventory its claims, build **three different figure families**, check them,
present a side-by-side sheet; the user picks; you finalize.

**Output location**: file `drafts/methods.md` → `drafts/methods_figures/`; pasted text →
`./figures/<slug>/`; multi-section/long input → one subfolder per passage `p1_<slug>/ …`; a
user-named folder → exactly that (`--out-dir`). Tell the user the path. One theme shared by all
passages (`--theme` or edit `theme.yaml` in the output root).

**B1 Scaffold + analyze**: `T new_figures drafts/methods.md [--theme t.yaml] [--split|--whole]
[--passages 1,3]` or `T new_figures --text "<passage>" --name rag_pipeline`. Prints per passage: word
count, equations, structure cues, three suggested families. ≤ 350 words without headings = one
passage. No figure-worthy structure (pure narrative)? Say so instead of forcing figures.

**B2 Inventory (NOTES.md)**: entities, ordered steps (with their verbs), relations (direction + verb),
quantities with units, qualifiers, conclusions — each with a short quote. Confirm the families
(REFERENCE §7): default = three layouts of the dominant structure (**detailed / compact overview /
alternative lens**); strong second structure → two + one; equations → the equation trio unless
incidental. The three must differ in **topology** (lanes / stack / radial / matrix / chart / plate), not
styling. For mathematical, scientific, algorithmic passages prefer **active demonstrations**
(populated matrix computation, continuous coordinate/metric spaces, Bayesian plates, causal DAGs)
over static bullet cards.

**B3 Write build.py** — three builders, each gets a fresh `Diagram` of its canvas size:
```python
from figlib import *
INFERRED = ["v1: ordinal ratings interpret the passage's qualitative wording"]   # reported to the user
ALLOWED_TERMS = ["layer"]                # structural words, not claims
LINT_IGNORE = []                         # warnings accepted on purpose (substring)
def v1(d):                               # swimlane pipeline
    lane(d, 20, 20, 1060, 175, "Offline indexing")
    chain(d, ["Inspection reports\n(scanned)", "OCR\nto text", "Semantic\nchunking"], 80, 78, 140, 60,
          shapes=["document", None, None], ids=["rep", "ocr", "chk"])
VARIANTS = [dict(key="v1", name="swimlane_pipeline", size=(1100, 400), build=v1,
                 about="one line for the sheet", caption="Draft caption in the passage's words."), ...]
```
Rules: theme roles only, same category = same style in all three; peers share sizes and one gap
(helpers, not hand-tuned numbers); connectors attached, feedback dashed/secondary; ≤ ~25 text items,
< ~150 vertices (else split into two figures); no in-figure title — write `caption`; labels in the
**passage's wording** (shorten by deletion, not synonym; keep qualifiers, digits, units, acronyms as
written). Interpretive devices (ratings, frontiers, "best fit", axis orderings, math facts not in the
text) only if listed in `INFERRED`.

**B4 Prototype, inspect, fix (≥ 2 rounds)**: `T prototype <passage dir> [--only v2] --note "…"` builds
all three, renders, lints, runs the faithfulness check, writes `prototypes.png/.md`, logs err/warn/miss.
**View each PNG** and the sheet. Fix every lint warning or add a deliberate `LINT_IGNORE`; resolve
each NOT-IN-PASSAGE word (reword with the passage's term · `ALLOWED_TERMS` if structural · `INFERRED`
if interpretation). Check what lint can't: arrows crossing labels, crowded corners, weak hierarchy,
unbalanced whitespace, two prototypes too similar, **every arrow's direction against the inventory**.
Done at 0/0/0 (or accepted warnings) and clean at full size.

**B5 Present**: show `prototypes.png`; per prototype one line on its emphasis, its draft caption, its
INFERRED items; point out source oddities (typos, inconsistent names) rather than fixing silently. Ask
the user to pick (or request changes / a combination → edit build.py, re-run).

**B6 Finalize**: `T finalize <passage dir> --pick v2 [--name rag_pipeline] [--clean]` → `<name>.drawio`
(+ .png) and `CHOSEN.md` (caption, inferred). `--clean` drops the other prototypes but keeps `_work/`.
Offer mode C for venue-specific polish.

---

## Mode C — enhance a .drawio for publication

One deliberate pass: **understand the figure's job → measure at print size → change it to serve that
job → verify → export.** Never edit before the interview.

**C1 Start**: `T start_enhance path/FIG.drawio [--source-image] [--text] [--artifacts DIR] [--theme]`.
It discovers context (mode-A work dir: source image, build.py, theme, NOTES; mode-B passage folder:
passage.md, build.py VARIANTS, CHOSEN.md, caption, INFERRED), detects **hand edits after generation**,
recommends a route, audits "before", writes `<stem>_enhance_work/` (context.md, before_audit.md,
brief.yaml, questions.md, theme.yaml, build_enhanced.py if rebuildable). Read context.md and the audit;
**view** `before.png` and `before_print_preview.png` (actual printed size); read/view the source
image/text — it is the ground truth for content.

**C2 Interview (don't skip)** from `WORK/questions.md` (pre-filtered, tailored; REFERENCE §12):
rounds of **≤ 3–4 questions per message**, options as buttons when available, always a default
("If unsure: Elsevier 1.5-column, grayscale-safe, Helvetica"). Never ask what the files already say.
Rounds: purpose & placement (purpose, domain, venue, width, takeaway) → audience & content (audience,
emphasis from the figure's own labels, text density, terminology) → visual style (active vs overview,
print mode, color-blind, font, palette) → math/labels/caption → origin-specific (image: fidelity
exact/polish/redesign, photos; text: inferred items, borrowing from other prototypes) → **plan
confirmation** in 4–8 bullets (route, layout changes, theme/font, size targets, math, caption).
Record as you go:
```bash
T brief WORK --set target.venue=ieee --set target.column=double --set target.print_mode=grayscale_safe \
  --set "style.font=Times New Roman" --set "intent.emphasis=[MASK] | Output:" --set "intent.takeaway=..." --resolve
```
`--resolve` → `width_in` / `min_font_pt` from venue presets (ask the user to confirm against the
author guidelines), grayscale/colorblind flags, palette/font applied to `WORK/theme.yaml`.

**C3 Route**: **rebuild** (default when a build script exists and no hand edits) — edit
`WORK/build_enhanced.py` (text origin: the chosen variant's function and its `size`; image origin: the
LAYOUT section, as far as fidelity allows), then `T rebuild WORK --passes fonts,sizes,strokes,align,attach,math,fit-page=12`.
**edit** (hand-edited or no build script) — `Doc.load` the figure, make structural changes in Python,
save to `"<stem>#ENHANCED.drawio"`, then `T enhance FIG -o OUT --theme WORK/theme.yaml --brief WORK/brief.yaml --all`
(or selected passes). The user's hand edits win: use edit route or ask before rebuilding.

**C4 Changes, big to small** (fix catalog REFERENCE §11):
1. **Print size**: at `width_in` every label ≥ `min_font_pt`; prefer shrinking the canvas/reflowing
   over inflating fonts in fixed boxes; aspect suits the column.
2. **Message & active form**: `intent.emphasis` gets the strongest visual weight, the rest muted;
   remove titles/decoration; turn static cards into active figures where the content allows; apply
   `text_density` (explanations → caption).
3. **Content**: terminology/renames/removals; text origin: keep/drop INFERRED as answered; image
   origin: respect `fidelity`.
4. **Theme**: palette + font; ≤ 3 hues + tints; grayscale/CVD safety by lightness, dashes, outlines;
   white background. Palette consolidation is a **decision**: write a mapping table and apply
   `T enhance … --colors --map "#hex=role@opacity" …`; the audit (`--reference` original) flags lost
   color categories.
5. **Math**: LaTeX everywhere once any is used (`d.equation` display, `\( … \)` inline), the paper's
   notation, math flag on.
6. **Typography & geometry**: one family, ≤ 6 theme sizes, aligned edges, equal gaps, attached
   connectors, 2–3 stroke roles, page fitted with 10–16 px margins.
7. **Caption** in `brief.content.caption`, consistent with panel labels and emphasis.
Log every deliberate change in `WORK/CHANGES.md` (passes append automatically).

**C5 Verify (repeat until clean)**: `rebuild` (or `T audit_drawio "FIG#ENHANCED.drawio" --brief
WORK/brief.yaml --theme WORK/theme.yaml --out-dir WORK --tag after`) gives a readiness score + issues
(legibility, color, typography, math, layout, connectors). **View `after_print_preview.png` at 100 %.**
Text origin: NOT IN SOURCE TEXT empty (or justified); image origin with exact/polish fidelity: fidelity
score must not collapse. Walk the manual checklist (REFERENCE §10). Accept a warning only on purpose:
add its substring to `review.accepted_warnings` and say why in CHANGES.md. Target ≥ 90, no
legibility/contrast/math issues.

**C6 Report + export**: `T report WORK --export pdf,svg,png` → `before_after.png`, `REPORT.md`, exports
`<stem>_ENHANCED.pdf/.svg/.png` (no `#` — it breaks `\includegraphics`). Show before/after, final
caption, changes, accepted/open items, file paths. Vector PDF/SVG need the draw.io CLI; otherwise tell
the user: draw.io → File → Export as → PDF/SVG, "Crop" checked.

---

## Gotchas
- Data URIs in styles are `data:image/png,<b64>` — **no `;base64`** (`;` breaks style parsing).
- Labels are HTML: markup escapes `<` `&`; `raw=True` does not.
- Quote `#` paths in shells (`"fig#ENHANCED.drawio"`); never use `#` in export names.
- `enhance --sizes` raises fonts and updates the work theme → re-check overflow ("label … wider than
  the box"). `--fit-page` moves content (image-fidelity compare runs before the passes).
- Unicode math symbols (∈) may be missing in fonts: use an equation label or words ("λ (0 to 1)").
- Coordinates read off a uniformly resized view: re-measure (or `coord_scale=(sx, sy)` as a stopgap).
- Venue presets are typical, not authoritative.
- More symptoms → fixes: REFERENCE §15.
