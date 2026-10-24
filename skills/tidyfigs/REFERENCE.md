# tidyfigs — reference

Companion to SKILL.md. `T` = `python drawio_toolkit.py` (or `python scripts/<tool>.py` after
`T unpack`). Sections: 1 Theme · 2 drawio_kit API · 3 figlib & build.py contract · 4 drawio_doc &
brief.yaml · 5 Tool CLIs · 6 Recipes (image features) · 7 Figure catalog (text) · 8 Equations & math ·
9 Faithfulness · 10 Style guide & checklists · 11 Fix catalog (enhance) · 12 Interview ·
13 Export · 14 draw.io file format · 15 Troubleshooting.

---
## 1. Theme

Keys (YAML / TOML / JSON; merged over built-in defaults): `colors{role: hex}`,
`fonts{key: {family, google?}}`, `default_font`, `sizes{role: px}`, `line_height`,
`strokes{role: px}`, `opacity{role: percent}`, `shape{corner_radius, shadow}`, `spacing{padding, gap}`.

Default theme (`assets/theme.yaml`, used by text and enhance modes; navy_default preset is identical):
```yaml
colors: {primary: "#19355d", secondary: "#4276b0", neutral: "#a4a4a4", text: "#000000", background: "#ffffff"}
fonts: {sans: {family: "Helvetica"}, serif: {family: "Times New Roman"}}   # google: true for Roboto/Inter
default_font: sans
sizes: {title: 20, heading: 15, subheading: 13.5, body: 13, label: 11.5, small: 10.5,   # px on the canvas
        equation: 30, eq_term: 20, eq_small: 16}
line_height: 1.2
strokes: {hairline: 0.75, thin: 1, normal: 1.5, thick: 2, heavy: 3}
opacity: {wash: 8, tint: 18, soft: 35, strong: 60}
shape: {corner_radius: 8, shadow: false}
spacing: {padding: 10, gap: 30}
```
Image mode (`assets/theme_image.yaml`) = same colors + `mono: Courier New`; sizes in **source px**
`{title: 28, heading: 20, subheading: 16, body: 14, label: 12, small: 10, caption: 18}`, strokes
`{hairline: .75, thin: 1, normal: 1.5, thick: 2.5, heavy: 4}`, opacity `{tint: 25, soft: 45, faded: 35}`,
gap 12. Sizes scale with `--scale`.

Presets (`assets/themes/`): **okabe_ito** (color-blind safe) primary `#0072b2`, secondary `#e69f00`,
neutral `#999999`, accent3 `#009e73`, accent4 `#d55e00`, accent5 `#cc79a7`, accent6 `#56b4e9`;
**grayscale** primary `#262626`, secondary `#6b6b6b`, neutral `#aaaaaa` (L* ≈ 20/45/70), opacity tint
22, soft 40, strong 65.

Venue presets (`assets/venues.yaml`; typical only — confirm with the author guidelines):

| venue | single | 1.5 col | double | min font | font |
|---|---|---|---|---|---|
| generic | 3.5 in | 5.0 | 7.0 | 7 pt | Helvetica |
| ieee | 3.5 | – | 7.16 | 8 pt | Times New Roman |
| elsevier | 3.54 (90 mm) | 5.51 (140 mm) | 7.48 (190 mm) | 7 pt | Helvetica |
| springer_lncs | 4.8 (122 mm) | – | 4.8 | 8 pt | Times New Roman |
| thesis | 6.0 | – | 6.5 | 9 pt | Times New Roman |
| slides | 10.0 | – | 13.33 | 18 pt | Helvetica |

Print arithmetic: printed pt = px × (width_in × 72 / canvas_px). A 1000-px canvas at 6.5 in → 1 px ≈
0.47 pt (body 13 px ≈ 6 pt is too small for most venues → narrow the canvas, don't inflate fonts).

---
## 2. drawio_kit API

```python
from drawio_kit import Diagram, Theme
d = Diagram(width, height, theme=None, scale=1.0, source=None, background="background", name="Page-1",
            grid=True, coord_scale=(1.0, 1.0), math=False)
d = Diagram.from_source("images/fig.png", theme="theme.yaml", scale=1.0)   # page size from the image
d.save("fig.drawio");  xml = d.to_xml()
t = Theme.load(path=None, overrides=None)   # overrides: same structure dict (figure-specific roles)
```
Coordinates: image mode = source px; text mode = canvas px (variant `size`); `scale` applied at save.
Every color arg takes a role, a hex (reported off-theme) or `"none"`; sizes a size role or number;
strokes a stroke role or number; opacities a role or percent. Every creating method returns the id.
`background=None` → transparent. `math=True` (or any `d.equation`, or `d.math_enabled = True`) turns on
draw.io LaTeX.

**Shapes**
```python
d.rect(x, y, w, h, label="", *, fill="background", stroke="text", sw="normal", rounded=False, dashed=False,
       dash=None, opacity=None, fill_opacity=None, stroke_opacity=None, shadow=None, gradient=None,
       gradient_dir="south", id=None, raw=False, extra=None, shape="rect", font=None, size="body",
       color="text", bold=False, italic=False, underline=False, align="center", valign="middle",
       wrap=True, spacing=None)
```
`rounded=True` → theme corner radius, number → radius px. `color` = label color. `spacing` = inner
padding. `wrap=False` keeps explicit breaks only. `extra={...}` raw draw.io style keys. `shape=` a
SHAPES key or raw base style.

| Helper | Notes |
|---|---|
| `d.shape(kind, x, y, w, h, label="", **rect_kw)` | `star, triangle, triangle_down, triangle_right, rhombus/diamond, hexagon, parallelogram, trapezoid, cylinder, document, cloud, process, note, card, actor, arrow_right, double_arrow, cross/plus, donut, step, callout_box`, or `"shape=mxgraph.aws4.lambda_function"` |
| `d.ellipse(x, y, w, h, label="", **kw)` · `d.circle(cx, cy, r, label="", **kw)` | circle = fixed aspect |
| `d.dot(cx, cy, r=4, fill="neutral", stroke="none", **kw)` | scatter marker |
| `d.star(cx, cy, size, fill="secondary", stroke="primary", **kw)` | 5-point star |
| `d.panel(x, y, w, h, title=None, *, header_h=None, header_fill="primary", header_color="background", title_size="heading", title_align="center", fill="background", stroke="text", sw="normal", rounded=False, header_band=True, header_opacity=None, shadow=None, id=None, **font)` | returns `(panel_id, (x, y, w, h_content))`; `header_band=False` = title line only |
| `d.callout(x, y, w, h, label, tip, *, base_width=40, base_at=None, fill="neutral", fill_opacity="soft", stroke="text", sw="normal", rounded=True, id=None, **font)` | box + pointer to `tip=(tx, ty)` from the facing side, centered at `base_at`; grouped |

**Text**
```python
d.text(s, x, y, *, w=None, h=None, anchor="center", size="body", font=None, color="text", bold=False,
       italic=False, underline=False, align=None, valign="middle", wrap=False, rotation=0, opacity=None,
       id=None, raw=False, pad=4, extra=None)
d.icon(glyph, cx, cy, size=24, **text_kw)          # emoji / unicode placeholder
d.equation(latex, x, y, *, w=None, h=None, anchor="center", size="body", color="text", align=None,
           opacity=None, id=None, pad=8, extra=None)   # native $$latex$$ label, auto-sized via mathtext
```
`(x, y)` is the anchor: `center, n, s, e, w, ne, nw, se, sw` (`anchor="w"` = left-aligned from x,
centered on y). Size auto-measured when `w/h` omitted; paragraphs: pass `w=` and `wrap=True`.
`rotation=-90` for vertical labels (about the box center; geometry is the unrotated box).
Markup: `**bold**` · `*italic*` · `__underline__` · `{role|text}` / `{#hex|text}` · `\n` · `\*`;
inline LaTeX `\( … \)`. `raw=True` = draw.io HTML as is (`<sup>`, small caps, letter-spacing).

**Connectors**
```python
d.edge(pts=(), src=None, tgt=None, *, color="text", sw="normal", arrow="end", head="block", head_size=6,
       dashed=False, dash=None, route="straight", exit=None, entry=None, label=None, label_size="label",
       opacity=None, id=None, extra=None)
d.line(pts, **kw)   # arrow=None        d.arrow(pts, **kw)   # arrow="end"
d.flex_arrow(pts, *, width=14, end_width=None, end_size=7, fill="primary", stroke=None, curved=True,
             opacity=None, id=None)    # wide block arrow; curved + waypoints = wavy band
```
`pts` = `[start if no src, *waypoints, end if no tgt]`: `edge([(0,0),(50,0),(50,40)])` free polyline ·
`edge([(50,0)], src="a", tgt="b")` one waypoint · `edge([(10,10)], tgt="b")` free start ·
`edge([], src="a", tgt="b")`. `arrow`: `end|start|both|None`; `head`: `block, classic, open, oval,
diamond, openblock, dash, none`. `route`: `straight` · `orthogonal` (elbow router) · `rounded` ·
`curved` (waypoints = quadratic control points). `exit/entry=(fx, fy)` fractions of the bounds:
`(1,.5)` right, `(0,.5)` left, `(.5,0)` top, `(.5,1)` bottom. Edges are always top-level (attach to
grouped vertices freely).

**Free-form geometry** (embedded SVG: movable/resizable, not node-editable)
```python
d.polygon(pts, *, fill="neutral", stroke="none", fill_opacity=None, stroke_opacity=None, sw="normal",
          smooth=False, closed=True, dash=None, id=None)      # smooth = Catmull-Rom through points
d.svg_layer(polys, id=None, pad=2)   # [{"pts": [...], "closed", "smooth", "fill", "fill_opacity", "stroke",
                                     #   "stroke_opacity", "sw", "dash"}, {"circle": (cx, cy, r), ...}]
d.surface_mesh(back, front, *, nu=30, nv=14, bulge=0.0, fill="secondary", fill_opacity="tint", line="primary",
               line_opacity=55, line_width="hairline", outline="primary", id=None)
```
`surface_mesh`: pseudo-3-D patch between two silhouettes (both left tip → right tip), `bulge` lifts the
middle. SVG bakes theme colors in → re-run the build after a theme change.

**Raster** (needs `from_source` for crops)
```python
d.image_crop((x0, y0, x1, y1), x=None, y=None, w=None, h=None, *, inset=1, upscale=2, fmt="jpeg",
             quality=85, border=None, id=None)       # fmt="png" for line art / transparency
d.image_file(path, x, y, w, h, *, border=None, id=None)
d.crop(bbox, upscale=2) -> PIL.Image;  d.save_crop(bbox, path, upscale=2)
```
`inset` trims the source's own border; `border=` draws a themed frame instead.

**Groups, lookup, layout**
```python
with d.group("tile_mt") as gid: ...          # vertices inside move together; nesting allowed
d.get(id) -> dict;  d.bbox(id) -> [x, y, w, h]
d.row(x, y, n, w, h, gap=None)               # n equal boxes left→right (gap default = spacing.gap)
d.row_widths(x, y, widths, h, gap=None)      # varying widths, one gap
d.fit_row(x0, x1, y, n, h, gap=None)         # n equal boxes exactly spanning x0..x1
d.column(x, y, n, w, h, gap=None);  d.grid_boxes(x, y, cols, rows, w, h, gx=None, gy=None)  # row-major
Diagram.snap(v, step=2)
Diagram.scatter_in_polygon(poly, n, keepout=(), min_dist=8, seed=0)    # keepout rects (x0, y0, x1, y1)
Diagram.scatter_along(fn, x0, x1, n, spread=10, min_dist=8, seed=0)    # near y = fn(x)
Diagram.scatter_blob(cx, cy, n, sx=20, sy=None, min_dist=8, seed=0)    # gaussian cluster
```
Module helpers: `catmull_rom(points, samples_per_seg=12, closed=False)`, `html_lines(value)`,
`measure_line(segments, family, size)`, `measure_math(latex, size) -> (w, h)`, `render_math`,
`find_font_file(family, bold, italic)`, `point_in_polygon(px, py, poly)`, `SHAPES`.
Theme resolvers: `t.color() t.size() t.stroke() t.opacity() t.font_family()`; `t.off_theme` collects
raw values. Style strings for hand edits: `Diagram(10, 10, theme=…)._shape_style(...)` / `_font_style(...)`.

---
## 3. figlib (text-mode components) and the build.py contract

`from figlib import *`; every function takes `d` first.

| Call | Draws / returns |
|---|---|
| `NODE, SOFT, DARK, MUTED, GHOST` | presets for `d.rect(..., **NODE)`: NODE white + primary outline (default step/entity) · SOFT secondary tint (second category) · DARK primary fill, white text (emphasis/outputs) · MUTED neutral tint, dashed (context, moderators) · GHOST no fill, dashed neutral (group frames); `style(NODE, size="label")` copies with overrides |
| `pill(d, cx, y, text, w=200, h=34, fill="primary")` | rounded column/stage header |
| `badge(d, cx, cy, n, r=13)` | numbered circle |
| `lane(d, x, y, w, h, title, band_w=38)` | swimlane with rotated title band → content box |
| `connect(d, a, b, side="h"\|"v", **edge_kw)` | arrow between mid-sides of two vertices |
| `chain(d, labels, x, y, w, h, gap=30, styles=None, ids=None, direction="h", shapes=None)` | equal boxes + arrows → ids |
| `cycle(d, labels, cx, cy, rx, ry, w=156, h=60, styles=None, badges=True, close=True)` | boxes on an ellipse, curved arrows, last→first dashed feedback → `(ids, centers)` |
| `layers(d, x, y, w, spec, layer_h=92, gap=26, tab_w=150, styles={i: preset})` | stacked layers `[(name, [components])]` → `(ids[(layer, comp)], layer_boxes)` |
| `frame(d, x, y, w, h, color="neutral", label=None)` | dashed group frame (arrows may connect to its id) |
| `bracket(d, x0, x1, y, color, up=False)` | term bracket → midpoint x |
| `spread(centers, width, gap, lo, hi)` | non-overlapping box centers |
| `annotated_equation(d, terms, cx, cy, notes_above, notes_below, size="equation", box_w=230, box_h=78, top_y=30, bottom_y=320)` | equation split into colored LaTeX terms `[(latex, role)]` with bracketed callouts `[(term_index, role, text)]` → term spans |
| `rating_dots(d, cx, cy, n, of=3)` · `rating_legend(d, x, y)` | ordinal dot ratings |
| `card(d, x, y, w, h, title, intro, sections=[(head, items, color, marker)], footer)` | grouped card |
| `continuum(d, x0, x1, y, left, right, left_eq, right_eq, marker, marker_label)` | gradient scale with marker |
| `legend(d, x, y, [(preset, label), ...], spacing=190)` | swatch legend |
| `axes(d, ox, oy, x1, y1, xlabel, ylabel, xticks=[(px, label)], yticks=[(px, label)])` | axes |
| `table(d, x, y, col_widths, headers, rows, row_h=52, cell=fn)` | zebra table; `cell(d, ri, ci, box)` may draw custom content (return True) |
| `eq(d, latex, x, y, **kw)` | shorthand for `d.equation` |

build.py contract (read by `prototype` / `finalize` / `start_enhance`):
```python
INFERRED = ["v1: ..."]           # content not stated in the passage → reported to the user
ALLOWED_TERMS = ["layer"]        # structural label words that are not claims
LINT_IGNORE = ["uneven gaps"]    # accepted lint warnings (substring)
VARIANTS = [dict(key="v1", name="swimlane_pipeline", size=(W, H), build=v1, about="...", caption="..."), ...]
```
Each `build(d)` gets a fresh `Diagram(W, H)` with the shared theme; `scale=` in a variant changes its
export scale. Theme lookup: passage dir → output root → `assets/theme.yaml`.
Image-mode build.py (from `assets/build_template_image.py`) reads `config.json` (source, out, theme,
scale, scripts) and edits only the LAYOUT section inside `build()`.

---
## 4. drawio_doc (edit existing files) and brief.yaml

```python
from drawio_doc import Doc
doc = Doc.load("fig#ENHANCED.drawio")              # compressed or plain
doc.vertices(); doc.edges(); doc.get("enc")
doc.find(text=r"^Encoder$", kind="vertex"); doc.find(style={"fillColor": "#19355d"})   # regex values
c = doc.get("enc")
c.plain, c.value, c.style, c.tokens, c.is_math, c.is_text, c.is_group, c.is_image
c.set_style(fillColor="#19355d", fontColor="#ffffff", fontStyle=1)   # None removes a key
c.value = "<b>Encoder</b>"                          # HTML (escape & < >)
c.abs_geo() -> [x, y, w, h];  c.set_abs_geo(x=..., y=..., w=..., h=...)
doc.move("enc", dx=4, dy=0); doc.translate_all(dx, dy)
doc.align(["a", "b"], "top")      # left|right|top|bottom|center-x|center-y (to the mean)
doc.distribute(["a", "b", "c"], "x");  doc.equalize(ids, width=True, height=True)
doc.remove("title")               # also children; detaches edges
doc.add_vertex(doc.new_id(), "<b>(a)</b>", "text;html=1;fontSize=14;", x, y, w, h)
doc.add_edge(doc.new_id(), "endArrow=block;html=1;strokeColor=#000000;", src="a", tgt="b", points=[(x, y)])
doc.page; doc.set_page(w, h); doc.content_bbox(); doc.math = True; doc.save(path)
```
brief.yaml sections: `figure` (name, input, origin, source_image, source_text, build_script, output;
optional variant/canvas overrides) · `intent` (purpose, domain, takeaway, audience, emphasis) ·
`target` (venue, column single|one_and_half|double|custom, width_in, min_font_pt, print_mode
color|grayscale_safe|grayscale, grayscale, colorblind) · `style` (theme, font, palette, panel_labels,
presentation_style) · `content` (fidelity exact|polish|redesign, text_density, terminology, inferred
keep|drop|itemized, photos, caption_mode, caption, merge_from_prototypes, allowed_terms) · `math`
(notation, equation_refs) · `review.accepted_warnings` · `plan` (route rebuild|edit, steps, approved).
`T brief WORK --set key=value` (`a | b` = list) `--resolve`.

---
## 5. Tool CLIs (`T <tool> --help` for all options)

| Tool | Usage |
|---|---|
| new_build | `IMAGE [--theme T] [--scale S] [--workdir D] [--force] [--no-inspect]` scaffold mode-A work dir + inspection |
| inspect_image | `{info,grid,zoom,palette,boxes,ocr,lines,probe,all} SRC …` (`zoom --box x0 y0 x1 y1 --factor 3 --step 10`; `all --out-dir D`) |
| iterate | `WORKDIR [--note TXT] [--no-snapshot]` build + render + compare + lint + history |
| compare | `SOURCE PREVIEW.png\|FILE.drawio [--out-dir D] [--tag T] [--cell PX] [--tol PX]` side/edges/heat + score |
| analyze_text | `PATH \| --text TXT [--split\|--whole] [--json OUT]` passages, equations, cues, suggested families |
| new_figures | `PATH \| --text TXT [--name N] [--out-dir D] [--theme T] [--split\|--whole] [--passages 1,3] [--force]` |
| prototype | `PASSAGE_DIR [--only v2] [--note TXT] [--no-sheet]` build + preview + lint + faithfulness + sheet |
| finalize | `PASSAGE_DIR --pick v2 [--name N] [--clean]` |
| start_enhance | `FIG.drawio [--source-image] [--text] [--artifacts DIR] [--theme T] [--suffix "#ENHANCED"]` |
| brief | `WORK --set key=value … [--resolve]` |
| rebuild | `WORK [--passes all\|fonts,sizes,…,fit-page=12] [--no-check]` → `#ENHANCED`, fidelity/faithfulness, audit |
| enhance | `FIG [-o OUT] --theme T --brief B [--colors --fonts --sizes --strokes --align --attach --math --fit-page M \| --all] [--map "#hex=role@op" …] [--add-roles] [--to-theme] [--update-theme] [--family F] [--tol PX] [--log MD]` |
| audit_drawio | `FIG [--brief B] [--theme T] [--out-dir D] [--tag after] [--width-in W] [--min-pt P] [--reference ORIG]` |
| report | `WORK [--export pdf,svg,png] [--dpi 300]` |
| render_preview | `FILE.drawio [-o PNG] [--scale S] [--width W] [--dpi 300] [--engine kit\|drawio]` |
| lint_drawio | `FILE.drawio [--theme T] [--scale S] [--json OUT]` (exit 1 on errors) |

Lint checks: structure, data URIs, theme drift (colors/fonts/sizes/strokes), text overflow,
overlapping text/shapes, text crossing borders, near-miss alignment (1–3 px), uneven gaps, widths
differing slightly. Audit areas: legibility, color, typography, math, layout, connectors → score /100.

---
## 6. Recipes — rebuilding figure features (mode A; useful in all modes)

**6.1 Measuring precisely.** Grid images give ±3 px; probe pixels for ±1 px:
```python
from PIL import Image; import numpy as np
a = np.asarray(Image.open(SRC).convert("RGB")).astype(int); g = a.mean(-1)
print([x for x in range(a.shape[1]) if g[150][x] < 200])    # dark columns on row y=150
print([y for y in range(a.shape[0]) if g[:, 100][y] < 215]) # dark rows on column x=100
navy = (a[..., 2] - a[..., 0] > 30) & (g < 140)              # color-selective mask
from scipy import ndimage; lab, n = ndimage.label(navy)
for s in ndimage.find_objects(lab): print(s[1].start, s[0].start, s[1].stop, s[0].stop)
```
Consecutive dark columns `[8, 9]` = 2-px border → edge at 8, `sw=2`. Curved band centerline: per
column mid of min..max of the band mask (skip text-contaminated columns). Light/thin features vanish
under dark thresholds: zoom or threshold on their specific color. Text size: OCR width-fit, verified
by the edges overlay (doubled outlines = wrong size/weight/position).

**6.2 Panels.** `d.panel(52, 110, 620, 570, "**1. Title**", header_h=70, header_fill="primary",
header_color="background", stroke="none", shadow=True)`; light header = `header_fill="neutral",
header_opacity=55, header_color="primary"`; title line only = `header_band=False`. Separate header +
body boxes = two `rect`s with the same x/width.

**6.3 Rows, grids, tiles.** Measure first/last edge + count, let helpers compute:
`d.fit_row(43, 318, 198, 3, 102, gap=9)`; tile = group of rect + icon (`y + 34`) + label (`y + h - 24`).
Second row reuses the first row's x and width. Lint "uneven gaps"/"widths differ slightly" must be gone.

**6.4 Flows.** `edge([], src, tgt)`; `exit=(1,.5), entry=(0,.5)` side to side; `route="orthogonal"`
for one elbow; explicit path `edge([(220,486),(240,486),(240,458),(264,458)], src="sys", exit=(1,.4))`;
labeled dashed `edge([], src, tgt, label="yes", dashed=True)`. `head_size ≈ visible head length / 1.5`.
Line weight: measured px → stroke role.

**6.5 Branching / fan-in.** Branch: one orthogonal edge per target with the same `exit` (draw.io
merges the trunk). Fan-in: explicit symmetric waypoints; distribute `entry` x-fractions evenly.

**6.6 Curves.** Single bend: one control point ~2× the desired bulge from the chord. To pass through
measured P1, P2: waypoints W1..W3 with mid(W1,W2)=P1, mid(W2,W3)=P2. Wavy band:
`flex_arrow([start, W1, W2, W3, end], width=…)`. Long smooth arc: sample every ~30 px. Closed loop:
`d.line(loop_pts, route="curved")` with first == last.

**6.7 Text.** Mixed weights `"**Best for:** Classification."`; colored lead-in
`"{secondary|**CHUNK A:**} Sound"`; left list `anchor="w"` per line; paragraph/caption `w=…, wrap=True,
anchor="w"` (no manual breaks unless semantic); small caps/superscripts/tracking via `raw=True` HTML.
Simple symbols can be Unicode (θ, ∑, ≤, x²) when the figure has no LaTeX; otherwise LaTeX (§8).

**6.8 Plots.** Measure the origin; axes = `d.arrow` with `head_size=5`; ticks from a data→px mapping;
bars = one rect per value; line chart = polyline; gridlines `color="neutral", sw="hairline", dashed=True`.
Vectors stay attached via an invisible anchor: `d.circle(ox, oy, 1, fill="none", stroke="none",
id="origin")` + `d.edge([], src="origin", tgt="pt")`. Real chart → derive positions from data.

**6.9 Scatter.** `scatter_in_polygon(poly, 190, keepout=label_rects, min_dist=12, seed=7)` in a group
of `dot`s; match density, radius, color, empty spaces. Data scatter: detect markers (label + centroids)
and place each.

**6.10 3-D.** Wireframe: back edges (thin, neutral) → surface → front edges. `surface_mesh(back,
front, nu=30, nv=14, bulge=38)` with 5–7-point silhouettes; tune bulge until the outline overlays; mesh
density ≈ source grid lines. Points on a surface: split behind/front groups around it.

**6.11 Photos.** Crop exactly at the photo border; crop only the pictorial part, rebuild text natively.

**6.12 Icons** (preference): draw.io library shape (`mxgraph.aws4/azure/kubernetes/cisco/flowchart/basic.*`)
→ geometric rebuild (gear = star + circle, `document`, `cylinder`, `actor`) → emoji `icon` placeholder
→ `image_crop`. Report which.

**6.13 Callouts, legends, tables, timelines.** `d.callout(1164, 478, 176, 76, "**RAG target:** …",
tip=(1228, 384), base_at=1232)`; legend rows = 12-px swatch rect + `anchor="w"` label every 22 px;
table = `grid_boxes(..., gx=0, gy=0)` cells with `stroke="neutral", sw="thin"`; timeline = line + dots +
`fit_row` label positions.

**6.14 Tints & effects.** Tints = role + `fill_opacity`; gradients `gradient="secondary"`;
`shadow=True`; glows/blur/gloss and decorative backgrounds: omit (report) or approximate at low opacity.

**6.15 Hand-drawn sources.** Rebuild clean geometry (snap with `Diagram.snap`); optional sketch look
`extra={"sketch": 1, "curveFitting": 1, "jiggle": 2}`.

**6.16 Large figures.** Build and iterate region by region; helper functions for repeated structures;
> ~600 vertices → `svg_layer`; one diagram per figure (ask before splitting/merging pages).

---
## 7. Figure catalog (mode B; also "redesign" in mode C)

Pick three different families. Default: detailed / compact overview / alternative lens of the dominant
structure; strong second structure → two + one.

| Structure | Cue words | Families (layout recipe) |
|---|---|---|
| Process / method | first, then, stage, is converted/encoded, at query time | `swimlane_pipeline` (1100×400; two 175-px lanes; 6 cols of 140 px, gap 30; lane-crossing edges through the 20-px gap) · `layered_architecture` (1060×600; 5 layers 92 px, 26 apart; 3 comps/layer via `fit_row`; feedback on the right margin, rotated label) · `stage_chain` (`chain` + `badge`) |
| Feedback / iteration | loop, feedback, tune, refine | `numbered_cycle` (940×680; ellipse rx 330 ry 240; 8 boxes 156×60; hub r≈108; legend bottom) |
| Causal / conceptual | drives, leads to, moderated by, informs | `causal_columns` (1150×500; 4 columns x=150/425/700/975; pill headers; dashed frames arrows connect to; moderators box below) · `stepped_funnel` (1040×610; strictly decreasing bands; side box for moderators) · `concept_map` (1060×640; hub center, inputs left, outputs right, context top, downstream bottom; one label per edge bundle) · `nested_containers` (`frame` + chips) |
| Comparison / trade-off | whereas, in contrast, best, least, no single … dominates | `rating_matrix` (1000×440; first col 220, criteria 190, rows 96; legend + conclusion pill) · `method_cards` (1020×500; three 313-px cards, 20-px gutters; conclusion banner) · `positioning_chart` (940×630; plot ~740×440; bubble size = third criterion) |
| Equation | `$$…$$`, `\[…\]`, environments, several `$…$` | `annotated_equation` (1100×500; baseline ≈ 205; callouts 230×78 at y 30 / 320; "where …" strip) · `computation_graph` (1120×470; inputs left, two paths, operator circles, result right) · `intuition_glossary` (1100×640; geometry \| continuum panels + symbol table) |
| Matrix / tensor | matrix, factorization, SVD, dot product, rank | `matrix_factorization_grid` (1140×560; populated V (5×5) ≈ W (5×2) × H (2×5); active row/col tinted + callout with scalar arithmetic) · `comparative_state_spaces` (1160×450; 2–3 coordinate panels ~350 px: orthogonal high-D vs low-rank subspace vs simplex) · `spectral_decomposition` (eigenvector / SVD axes) |
| Geometric / metric | metric, Euclidean, cosine, manifold, geodesic, clustering | `metric_geometry_clusters` (1140×540; unit arc r≈140, vectors u v, chord vs angle, centroid attraction) · `divisive_density_clustering` (1120×480; SVD splitting hyperplane \| density cores, ε buffer, noise points) · `manifold_projection_spaces` (1120×460; ℝ^d manifold → 2-D embeddings, local vs global preservation) |
| Mechanistic / causal flow | causal, DAG, pathway, flux, compartmental, SIR | `causal_dag` (signed paths, confounder conditioning; rect = observed, ellipse = latent) · `reaction_pathway` (fluxes, activation/inhibition) · `compartmental_flow` (state boxes, rates, feedback) |
| Probabilistic / Bayesian | prior, posterior, plate, generative, latent, Markov | `hierarchical_generative_plate` (1100×500; nested plates with counts D/N/K; shaded = observed, open = latent, dots = hyperpriors outside) · `markov_state_graph` · `probabilistic_simplex` |
| Hierarchy / taxonomy | consists of, types of, categories | `tree` (`chain(direction="v")` + `connect`) · `nested_boxes` (`frame` in `frame`) · `outline_columns` (`pill` + `column`) |
| Temporal | years, since, phases, eras | `timeline` (line + dot + `fit_row`) · `phase_bands` (tinted rects over time) |
| Quantitative results in the text | %, increased, accuracy, F1 | `dot_or_bar_chart` (**only** stated values) · `results_table` · `before_after` (slope lines) |

Genuinely different = different reading direction/topology, level of detail, or lens (mechanism vs
meaning vs trade-off). Same theme, fonts, vocabulary across all three — the user chooses structure.

---
## 8. Equations and math

- Copy LaTeX verbatim from the passage/paper; never retype from memory.
- `d.equation(latex, x, y, size="equation"|"eq_term"|"eq_small", color=role)` → native `$$…$$`
  (MathJax, editable). Inline in prose labels: `"**Semantic weight** \\(\\lambda\\)"`. Both measured
  and previewed with matplotlib mathtext (supports `\frac \sqrt` sub/sup, Greek, `\mathbf \mathrm
  \text \lVert\rVert \sum \int \left(\right) \cdot \in \leq`). MathJax-only (`\color \textcolor
  \boldsymbol cases \underbrace`) render in draw.io but preview approximately — prefer splitting
  into terms over `\underbrace`.
- Color-code by giving each term its own label with `color=` (positions known, lint can check).
- Once a figure has any LaTeX, write every symbol in LaTeX (audit flags Unicode λ θ ≤ next to LaTeX).
  Plain figures may use Unicode; "λ ∈ [0, 1]" → "λ (0 to 1)" if ∈ is missing from the font.
- Match the paper's notation: `\mathbf{q}` vs `\boldsymbol{q}`, upright operators (`\mathrm{sim}`,
  `\operatorname{BM25}`), parameter names/values; record conventions in `brief.math.notation`.
  "Eq. (3)" references only if the user gives numbers.
- Sizes at print: displayed equations ≈ 1.3–1.8 × body (e.g. 12–14 pt with 8–9 pt labels);
  in-diagram ≈ body.
- **Equation trio**: (1) `annotated_equation` — split at top-level + − = and the factors the text
  explains; each note's wording from the defining sentence; weights/parameters above, quantities
  below, sub-definitions in a "where …" strip. (2) `computation_graph` — inputs → operations (boxes/
  circles with small equations) → result (DARK); one path per additive term; parameters as dashed side
  boxes feeding the operators they scale. (3) `intuition_glossary` — the geometric/limiting-case meaning
  the text gives (`continuum()` for λ = 0 / 1 / best) + `table()` symbol | meaning | range with
  equation cells. Math facts not in the text (cosine ∈ [−1, 1]) → INFERRED.
- Several equations: derivation → `stage_chain` of equation cards with the text's justification under
  each arrow + annotated final equation; system → `table()` with meaning column, or a computation graph
  if they feed each other; incidental equation in a process → small `d.equation` inside its step box.
- **Active demonstrations** (preferred for math/science content): populated matrices with realistic
  values, zero vs non-zero cells, active row i / column j with a callout of
  \(V_{ij} \approx \sum_r W_{ir}H_{rj}\); continuous axes with unit arcs (\(\lVert u\rVert_2 = 1\)),
  angular vs chord distance (\(\lVert u-v\rVert_2^2 = 2-2\cos\theta\)), centroid vectors \((x-\mu_i)\)
  for WCSS/SSE; plate notation (shaded observed w, open latent z θ φ, small dots for α β); DAGs with
  signed coefficients. Illustrative numbers/points are INFERRED.

---
## 9. Faithfulness (text origin)

Figures are read as claims; every label must trace to the source text.
- Inventory before building: entities (exact names/abbreviations; expand acronyms only if the text
  does), ordered steps with verbs, relations with direction + verb, quantities (digits and units
  exact), qualifiers (don't upgrade "reasonably" to "well"), conclusions.
- Prefer the passage's words; shorten by deletion. Don't add categories, steps, examples, numbers,
  citations. Interpretations (ratings, frontier, "ideal" corner, best-fit advice, axis ordering, math
  facts) only via `INFERRED`, reported to the user. Structural non-claims → `ALLOWED_TERMS`.
- The automatic check (prototype / rebuild / `faithful.faithfulness(drawio, text, allowed)`) lists label
  words absent from the passage (light stemming; acronyms match expansions). It is lexical: it can't
  catch a wrong relation between correct words — re-read every arrow against the inventory.
- Examples of fixes: "OCR text extraction" → "OCR to text"; "similarity search" → "Retrieve top-k
  similar chunks"; "increasing intervention" → "preventive → major rehabilitation"; invented "Best fit
  when … is paramount" → rebuilt from the passage's closing sentence.

---
## 10. Style guide and checklists

**Layout**: one idea per figure; ≤ ~25 text items (audit: ≤ ~35, labels ≤ ~16 words); reading order
left→right / top→bottom; feedback visibly different (dashed, secondary); grid-aligned via helpers;
margins ≥ 20 px while building (fitted page 8–20 px, typically 10–16), ≥ 24 px between callouts;
nothing outside the canvas; arrows never cross text (route with waypoints); edge labels sparingly
(one per bundle); no in-figure title.
**Color**: `primary` main path/emphasis, `secondary` second category, `neutral` context, `text`
labels; tints `wash/tint/soft`; ≤ 3 hues + tints; same category = same color everywhere; never color
alone (pair with position, dashes, labels, legend); dark fills → white text, tints → dark text.
**Typography**: theme sizes only; body ≥ 13 px and small ≥ 10.5 px on a 1000-px canvas; for 3.5-in
single column use a ~600–700-px canvas rather than smaller text; **bold** key noun, *italic*
qualifiers/examples; sentence case; no terminal periods in box labels; abbreviations as in the source.
**Shapes**: rounded rects for steps/entities, pills for headers, dashed frames for groups, cylinders
for databases, document shapes for documents; strokes `normal` boxes, `thick` arrows, `heavy`
inter-stage arrows, `thin` frames.

**Image-conversion quality checklist**: every source string present and spelled as in the source
(keep typos, mention them) with right weight/size/color role; rows/columns share y/x, size, gap;
connectors attached, arrowheads at the right ends; no off-theme values, ≤ ~8 color and ≤ ~7 size
roles; native except documented embeds/placeholders; output at `<image>.drawio`, work dir kept,
final iteration is the best.

**Academic-readiness — automatic (audit)**: every label (math too) ≥ min pt at target width; strokes
≥ 0.5 pt; rasters ≥ 300 dpi at print size; ≤ 3 hues + tints, no off-theme colors; text contrast ≥ 4.5:1
(≥ 3:1 large/bold); categories separable in grayscale (if required) and under deuteranopia/protanopia
(≥ 12 L* apart or outline/dash); ≤ 2 families, ≤ 6 sizes, sizes = roles; math flag on, LaTeX parses, no
Unicode/LaTeX mix; lint clean; page fitted; no title; no dangling connectors; ≤ 3 stroke widths, ≤ 2
arrow-head sizes.
**Manual (view the print-size preview at 100 %)**: takeaway visible in 5 s (emphasis = strongest
weight); reading order obvious, feedback distinct; terminology/symbols identical to the paper; notation
matches (bold vectors, upright operators); panel labels consistent with the caption; nothing relies on
color alone; white background, no shadows/glows unless the venue uses them; text origin faithfulness
clean, inferred handled; image origin with exact/polish: structure still matches the source; exports
vector, filenames without `#`.

---
## 11. Fix catalog (mode C)

Route: **rebuild** (edit `WORK/build_enhanced.py`, `T rebuild`) when a build script exists and no hand
edits — structural changes are far easier; otherwise **edit** (`drawio_doc` + `T enhance`).

| Issue | Rebuild route | Edit route |
|---|---|---|
| fonts too small at print | shrink canvas (`VARIANTS size` / panel widths) so px→pt grows; keep theme sizes | `enhance --sizes`, then widen overflowing boxes |
| overflow after size increase | widen boxes, `fit_row` with fewer columns, shorter labels | `set_abs_geo(w=…)`, `doc.distribute` |
| too many hues / off-theme | theme roles; tints via `fill_opacity` | mapping table → `enhance --colors --map "#d7ecd6=secondary@25" …`; unmapped distinct colors are kept (`--add-roles` writes them to the theme) |
| "categories dropped from N to M" | restore, or accept in `review.accepted_warnings` with a reason | same |
| grayscale-unsafe categories | one category dashed outline or lighter tint | `set_style(dashed=1)` / `fillOpacity` |
| mixed fonts | theme `default_font` | `enhance --fonts [--family …]` |
| near-miss alignment, uneven gaps | `row/column/fit_row/grid_boxes` | `enhance --align`, `doc.align/distribute/equalize` |
| dangling connector ends | `edge([], src=, tgt=)` | `enhance --attach` |
| whitespace / content at edge | adjust canvas | `enhance --fit-page 12` |
| in-figure title | delete; put in `content.caption` | `doc.remove(id)` |
| long explanatory labels | key noun phrase; rest → caption | `c.value = "<b>…</b>"` |
| emphasis missing | DARK preset / thicker stroke / larger size; mute others (neutral) | `set_style(fillColor=primary, fontColor=background)` |
| Unicode math next to LaTeX | `\( \lambda \)` or `d.equation` | replace label text, `doc.math = True` |
| notation differs from paper | edit LaTeX strings | same, in labels |
| panel labels missing | "(a) …" in panel titles or bold text top-left | `doc.add_vertex(...)` |
| low-res photo crop | `d.image_file` from a higher-res original | set the cell's `image=` |
| tall figure for single column | reflow side by side / two-row grid | usually rebuild |
| decorative elements | drop unless meaningful | `doc.remove` |
| static cards / text-heavy columns | transform into an active figure (§8 active demonstrations; §7 matrix/metric/plate/DAG families) | rebuild strongly recommended |

Active transformations: V ≈ W × H bullets → populated grids with highlighted row/column + dot-product
trace and non-negativity/sparsity note; distance-metric prose → 2-D frame (e₁, e₂), unit arc, θ vs
chord, centroid vectors; divisive clustering (PDDP) → SVD principal eigenvector v₁ + splitting
hyperplane; density clustering (HDBSCAN) → core clusters with buffer rings + explicit noise points;
dimensionality reduction → ℝ^d manifold projecting to 2-D (t-SNE local neighborhoods vs UMAP global
structure); generative descriptions → plate notation.

---
## 12. Interview (mode C)

Rules: start from `WORK/questions.md`; rounds of ≤ 3–4 questions, multiple-choice buttons when
available (else a short numbered list), one round per message, always a default; "you decide" →
record defaults explicitly; never ask what files already tell (origin, theme, caption, equations
present); free-text questions in their own round or last; record immediately with `T brief`; stop when
the brief has purpose, takeaway, venue + column, print mode, colorblind, font, palette, density,
caption mode + origin-specific items.

Question bank (→ brief key; applies):
1. **Purpose & placement** — figure's job: method/system overview · conceptual framework · comparison ·
   explaining an equation · results/evidence · graphical abstract (`intent.purpose`) · field: CS/AI/ML ·
   physics/engineering · biology/medicine · chemistry/materials · economics/finance · social science/
   causal inference · math/statistics · other (`intent.domain`) · venue: IEEE · Elsevier · Springer LNCS ·
   thesis · other (`target.venue`) · width: single · 1.5 · double · custom (`target.column`) · takeaway in
   one sentence, free text (`intent.takeaway`).
2. **Audience & content** — specialists · broad engineering · interdisciplinary (`intent.audience`) ·
   which part stands out (options = the figure's own key labels; `intent.emphasis`) · text inside:
   keep · shorten + move explanations to caption · minimal (`content.text_density`) · terms/symbols that
   must match the paper, renames/removals, free text (`content.terminology`).
3. **Visual style** — presentation: (recommended) active graphical demonstration · high-level
   structural overview (`style.presentation_style`) · print: color only · must work in grayscale ·
   grayscale only (`target.print_mode`) · color-blind safe: yes (recommended) · not needed
   (`target.colorblind`) · font: Times New Roman · Helvetica/Arial · Latin Modern/Computer Modern ·
   keep (`style.font`) · palette: keep · mine (hex) · Okabe-Ito · grayscale (`style.palette`).
4. **Math, labels, caption** — notation: keep · match my paper · plain-text symbols (if math) ·
   equation numbers: no · yes (if math) · panel labels: none · (a), (b) · bold a, b (if multi-panel) ·
   caption: use draft · I'll provide · write from the paper text (`content.caption_mode`).
5. **Origin-specific** — image: fidelity exact · polish · redesign (`content.fidelity`); photos: keep ·
   replace with higher-res · remove (if rasters); text: inferred items keep · drop · item by item
   (if any); borrow from other prototypes (free text).
6. **Confirm** the plan (4–8 bullets) → `plan.approved`.

Answer → consequence: domain → field idioms (units/vector fields for physics; compartments/receptors
for bio; signed causal arrows for economics; populated matrices and metric spaces for CS/math) ·
active presentation → transform static cards (§11) · venue + column → width_in, min_font_pt → canvas
width / sizes · takeaway → emphasis (DARK fill, thicker outline, position) + de-emphasis · general
audience → expand abbreviations, fewer symbols · move to caption → labels ≤ 6 words, explanations to
the caption draft · grayscale → lightness ≥ 12 L* apart or outline/dash · colorblind → no red/green
pairs, Okabe-Ito if hues are needed · Times/Latin Modern → theme default font (MathJax already matches
LaTeX) · fidelity exact → formatting only, keep positions (enhance passes, no rebuild) · polish →
rebuild allowed, keep structure + reading order · redesign → new layout, §7 families apply ·
inferred drop → remove each INFERRED element, re-run faithfulness.

---
## 13. Export and file names

- Masters: mode A `<image>.drawio` + `<image>#drawio.png` (300 dpi); mode C `<name>#ENHANCED.drawio`
  (`--suffix` to change). `#` breaks LaTeX `\includegraphics` and URLs → exports use `_`:
  `<name>_ENHANCED.pdf/.svg/.png`.
- Vector (preferred): `T report WORK --export pdf,svg` uses the draw.io desktop CLI (`drawio --export
  --format pdf --crop …`; `xvfb-run` on headless Linux). Without it: draw.io → File → Export as →
  PDF/SVG, "Crop" checked ("Include a copy of my diagram" optional).
- Raster: 300 dpi at target width (`--dpi 300`), 600 dpi for line art if the venue asks.
- Fonts embed in PDF/SVG only if installed on the exporting machine; check the PDF at 100 % at the
  printed width before submission.

---
## 14. draw.io file format cheat sheet (for `extra={…}`, hand-written XML, debugging)

```xml
<mxfile host="app.diagrams.net"><diagram id="p1" name="Page-1">
  <mxGraphModel pageWidth="1408" pageHeight="736" background="#ffffff" math="0" grid="1"><root>
    <mxCell id="0"/><mxCell id="1" parent="0"/>                                  <!-- default layer -->
    <mxCell id="box" value="&lt;b&gt;Encoder&lt;/b&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#19355d;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="275" y="455" width="170" height="62" as="geometry"/></mxCell>
    <mxCell id="e1" style="endArrow=block;html=1;exitX=0.5;exitY=0;entryX=0.5;entryY=1;" edge="1" parent="1" source="box" target="mask">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="108" y="486" as="sourcePoint"/>                      <!-- only when not attached -->
        <Array as="points"><mxPoint x="240" y="486"/></Array></mxGeometry></mxCell>   <!-- waypoints -->
  </root></mxGraphModel></diagram></mxfile>
```
Document order = z-order. Group/container children use parent-relative coordinates. `value` is
XML-escaped HTML when `html=1`. draw.io desktop may compress `<diagram>` (base64(deflate(urlencode(xml))));
the toolkit reads both. Style = `key=value;` pairs + bare tokens (`text;`, `ellipse;`, `group;`), no
spaces, values can't contain `;`.
Vertex keys: `fillColor strokeColor fontColor` (#rrggbb/none) · `strokeWidth` · `opacity fillOpacity
strokeOpacity textOpacity` (0–100) · `rounded=1` + `arcSize` (% of smaller side; with
`absoluteArcSize=1` = 2 × radius px) · `dashed=1;dashPattern=6 4` · `shadow glass sketch` ·
`gradientColor gradientDirection` (south/north/east/west) · `rotation` · `aspect=fixed` ·
`shape=image;image=data:image/svg+xml,<b64>;imageAspect=0` (+ `imageBorder`) · `container=1;collapsible=0`.
Text keys: `html=1` · `whiteSpace=wrap|nowrap` · `fontFamily fontSize` · `fontStyle` bits 1 bold 2
italic 4 underline · `align` · `verticalAlign` · `labelPosition verticalLabelPosition` · `spacing*` ·
`labelBackgroundColor` · `fontSource` (URL-encoded Google Fonts CSS).
Edge keys: `edgeStyle=none|orthogonalEdgeStyle|elbowEdgeStyle|entityRelationEdgeStyle` · `curved=1` ·
`rounded=1` · `endArrow startArrow` (block classic open oval diamond dash none) · `endFill startFill` ·
`endSize startSize` · `exitX/exitY entryX/entryY` (+ `exitDx`…) · `jumpStyle=arc` ·
`shape=flexArrow;width=;endWidth=;endSize=`.
Base shapes: `ellipse rhombus triangle;direction=… hexagon cylinder3 document cloud process note card
parallelogram trapezoid step umlActor singleArrow doubleArrow cross doubleEllipse swimlane;startSize=30`,
`mxgraph.basic.* mxgraph.flowchart.* mxgraph.aws4.* mxgraph.azure.* mxgraph.gcp2.* mxgraph.kubernetes.*
mxgraph.cisco.* mxgraph.networks.* mxgraph.office.*` (icons with `verticalLabelPosition=bottom;
verticalAlign=top;aspect=fixed`). Layers: `<mxCell id="L2" parent="0"/>`; prefer groups unless asked.

---
## 15. Troubleshooting

| Symptom | Cause → fix |
|---|---|
| everything offset/scaled one way | coordinates from a resized view → re-measure on the grids or numerically (`coord_scale` only as stopgap) |
| low score, side-by-side fine | photos/meshes/scatter/glows depress edge F1 → judge visually, use the heat map |
| red/cyan doubled text outlines | size, weight or vertical position off → OCR width-fit, bold vs regular, align `cy` to the bbox center |
| text wraps differently in draw.io | box too narrow or `wrap` on a short label → widen, `wrap=False`, breaks only where the source has them |
| arrow stops short / overlaps | free endpoint or wrong port → attach `src`/`tgt`, set `exit`/`entry` |
| curve bulges in the wrong place | waypoints treated as on-curve → they are control points (§6.6) |
| weird elbow routing | no port constraints → add `exit`/`entry`, or explicit waypoints with `route="straight"` |
| images missing in draw.io | `;base64` or raw `;` in style → use `image_crop`/`svg_layer` (lint reports) |
| `KeyError: Unknown color role` | role not in theme → add a semantic role to theme.yaml |
| off-theme warnings | raw hex/sizes in the build → move into roles (icon glyph sizes ignored) |
| emoji grey / small caps, LaTeX odd in preview | renderer limitation → check in draw.io (`--engine drawio`) |
| draw.io slow | > ~600 vertices → merge decorative marks into one `svg_layer` |
| group moves, arrow doesn't | arrow not attached → attach it |
| YAML theme fails | PyYAML missing → `pip install pyyaml` or TOML/JSON theme |
| OCR empty | no tesseract → read text from zooms; size via `measure_line` against bbox widths |
| `boxes` merges shapes | touching shapes → zoom + numeric probes |
| unusual shape previews as rectangle | renderer fallback → check in draw.io; labels/connectors still compared |
| overflow after `--sizes` | widen boxes / reflow; audit reports "label … wider than the box" |
