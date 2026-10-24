# tidyfigs — worked examples

Companion to SKILL.md / REFERENCE.md. The complete, runnable set ships inside `drawio_toolkit.py`
(`T unpack ./tidyfigs` → `examples/`). This file shows the patterns worth copying.

## Index

| Example | Mode / tier | Demonstrates |
|---|---|---|
| `01_two_panel_simple.py` | A, tier 1 (1408×736 BERT vs GPT; score 0.90) | header bands, `row_widths`, attached + elbow connectors, faded box, mixed bold captions, figure roles via `THEME` overrides |
| `02_tile_dashboard.py` | A, tier 2 (1024×559 NLP/NLU/NLG infographic; 0.87) | per-panel tint roles, tiles as groups, `fit_row` with identical margins/gaps, emoji icons, branching NLI connectors, fan-in with waypoints, bullets, footer rule |
| `03_vector_space_plot.py` | A, tier 3 (616×295; 0.98) | wavy `flex_arrow`, axes, rotated label, invisible anchor for attached vectors, dashed cluster circle, attached pointers |
| `04_complex_manifold.py` | A, tier 4 (1408×768; 0.80) | `surface_mesh`, wireframe z-order, `scatter_in_polygon`/`scatter_along`, `image_crop`, translucent beams, stars, callouts, small-caps title, serif caption |
| `A_methods_pipeline/` | B, process + feedback | swimlane pipeline · layered architecture · numbered cycle |
| `B_conceptual_framework/` | B, causal framework | causal columns · stepped funnel · concept map |
| `C_comparison/` | B, trade-offs | rating matrix · method cards · positioning chart (5 INFERRED items) |
| `D_equation/` | B, LaTeX equation | annotated equation · computation graph · intuition + glossary |
| `E_matrix_computation/` | B, NMF vs LDA | populated matrix factorization grid · comparative feature spaces · Bayesian plate (own theme.yaml) |
| `F_metric_manifold_geometry/` | B, metrics & manifolds | metric geometry clusters · divisive & density clustering · manifold projection (own theme.yaml) |

Run: `python examples/01_two_panel_simple.py [--image SRC] [--out OUT.drawio] [--theme T] [--scale S]`
(without `--image`, photo crops become labeled placeholders) · `T prototype examples/A_methods_pipeline`.
In image examples, figure-specific roles sit in a `THEME = {...}` override; in a real conversion put
them in the work dir's theme.yaml (otherwise lint reports them as off-theme). E and F carry in-figure
titles — drop those for a paper (mode C does).

Lessons from building them:
- 03 first used coordinates eyeballed on a resized view (score 0.78, panels 70 px too wide);
  re-measuring on the true pixel grid (zoom + numpy probes) gave 0.98.
- 01 initially had strokes and font sizes ~40 % too small; the edges overlay made it obvious.
- 02's lint flagged 1–3 px misalignments between panels; unifying margins, gaps and tile heights fixed
  them without changing the look.
- Faithfulness catches: A "OCR text extraction" / "similarity search" were paraphrases → passage
  wording; B "increasing intervention" not in the text → "preventive → major rehabilitation"; C invented
  "Best fit when … is paramount" → rebuilt from the closing sentence, the rest listed in INFERRED;
  D callouts aligned to equation terms are intentionally uneven → `LINT_IGNORE`.

---
## Mode A, tier 1 — `01_two_panel_simple.py` (complete)

`_common.run(layout, size, THEME, name)` parses `--image/--out/--theme/--scale`, loads
`assets/theme_image.yaml` + overrides, builds the Diagram (`from_source` when an image is given), calls
`layout(d)` and saves. In a real conversion the same calls go into the work dir's `build.py`.

```python
#!/usr/bin/env python3
"""
Tier 1 — simple two-panel comparison (BERT auto-encoding vs GPT autoregressive), 1408x736 source.
Shows: header bands, token boxes in a row with equal gaps, attached connectors, elbow arrow,
partially faded box, mixed bold/regular captions, figure-specific theme roles.
"""
from _common import run

THEME = {  # figure-specific roles layered over the user's theme
    "colors": {"canvas": "#eef1f5", "token": "#d6d6d6", "ghost": "#e9e9e9"},
    "sizes": {"title": 42, "heading": 28, "body": 27, "caption": 25},
    "strokes": {"normal": 4, "thick": 6, "heavy": 9},
}


def layout(d):
    d.background = "canvas"
    d.text("**Transformer Architectures: Two Paths to Language**", 704, 45, size="title", color="primary")
    for side, x0, title, block, caption in (
        ("L", 52, "AUTO-ENCODING (e.g., BERT)", "Encoder",
         "**Bidirectional context.**\nLearns by filling gaps.\n**Best for:** Understanding & Classification."),
        ("R", 750, "AUTOREGRESSIVE (e.g., GPT)", "Decoder",
         "**Unidirectional order.**\nLearns by predicting next word.\n**Best for:** Generation & Creation."),
    ):
        d.panel(x0, 110, 622, 570, title, header_h=70, header_fill="primary", header_color="background",
                title_size="heading", stroke="none", shadow=True, id=f"panel{side}")
        cx = x0 + 311
        d.text(caption, cx + (0 if side == "L" else -2), 592, size="caption", id=f"cap{side}")

    tok = dict(fill="token", stroke="text", sw="normal", rounded=4, size="body")
    # left: input row with [MASK], predicted token above, encoder below
    d.text("**Input:**", 120, 367, size="body")
    xs = d.row_widths(182, 336, [97, 138, 97, 97], 62, gap=13)   # one constant gap, measured widths
    for (x, y, w, h), t in zip(xs, ["[A]", "[MASK]", "[C]", "[D]"]):
        if t == "[MASK]":
            d.rect(x, y, w, h, "**[MASK]**", fill="primary", stroke="secondary", color="background",
                   rounded=4, size="body", id="L_MASK")
        else:
            d.rect(x, y, w, h, t, id=f"L_{t[1]}", **tok)
    mask_cx = xs[1][0] + xs[1][2] / 2
    d.rect(mask_cx - 48, 218, 96, 62, "[B]", id="L_B", **tok)
    d.rect(mask_cx - 85, 455, 170, 62, "**Encoder**", fill="primary", stroke="primary", color="background",
           rounded=4, size="body", id="Enc")
    d.edge([], src="L_MASK", tgt="L_B", color="secondary", sw="thick", exit=(.5, 0), entry=(.5, 1))
    d.edge([], src="Enc", tgt="L_MASK", sw="thick", exit=(.5, 0), entry=(.5, 1))
    d.edge([(108, 486)], tgt="Enc", sw="thick", entry=(0, .5))

    # right: input row with faded last token, decoder -> output -> [D]
    d.text("**Input:**", 822, 249, size="body")
    xs = d.row(885, 218, 4, 97, 62, gap=12)
    d.rect(xs[3][0] + xs[3][2] - 10, 218, 38, 62, fill="ghost", stroke="ghost", rounded=4, opacity="faded")
    for (x, y, w, h), t in zip(xs, ["[A]", "[B]", "[C]", "[D]"]):
        d.rect(x, y, w, h, t, id=f"R_{t[1]}", opacity=75 if t == "[D]" else None, **tok)
    d.rect(978, 336, 197, 62, "**Output:**", fill="primary", stroke="secondary", color="background",
           rounded=4, size="body", id="Out")
    d.rect(978, 455, 197, 62, "**Decoder**", fill="primary", stroke="primary", color="background",
           rounded=4, size="body", id="Dec")
    d.edge([], src="Dec", tgt="Out", sw="thick", exit=(.5, 0), entry=(.5, 1))
    d.edge([(810, 486)], tgt="Dec", sw="thick", entry=(0, .5))
    d.edge([], src="Out", tgt="R_D", color="secondary", sw="thick", route="orthogonal", exit=(1, .5), entry=(.5, 1))

    # divider + direction glyph arrows
    d.line([(710, 110), (710, 715)], color="neutral", sw="thick")
    d.arrow([(330, 676), (395, 676)], color="primary", sw="heavy")
    d.arrow([(395, 706), (330, 706)], color="primary", sw="heavy")
    d.arrow([(1020, 692), (1103, 692)], color="primary", sw="heavy")


if __name__ == "__main__":
    run(layout, (1408, 736), THEME, "01_two_panel_simple")
```

## Mode A, tier 3 — `03_vector_space_plot.py` (complete)

```python
#!/usr/bin/env python3
"""
Tier 3 — conceptual plot / geometry (discrete entities -> continuous vector space), 616x295 source.
Shows: wavy wide arrow (flex_arrow; curve waypoints are CONTROL points), axes with arrowheads,
rotated axis label, invisible anchor so vectors stay attached when points move, dashed cluster
circle, annotation pointers attached to shapes, header bands using a neutral fill at reduced opacity.
All coordinates were measured on the true pixel grid (inspect_image.py zoom / numeric probes).
Tip: run with --scale 2 (the source is small).
"""
from _common import run

THEME = {"sizes": {"heading": 13.5, "body": 15, "subheading": 13, "caption": 12, "label": 12, "note": 10.5, "axis": 8.5},
         "strokes": {"normal": 1.5, "thick": 2.5}}


def layout(d):
    # ---- panel 1: discrete entities
    d.panel(8, 9, 189, 275, "1. Discrete Entities (Input)", header_h=34, header_fill="neutral", header_opacity=55,
            header_color="primary", title_size="heading", stroke="neutral", sw="thick", id="p1")
    for (x, y, w, h), t in zip(d.column(57, 66, 3, 91, 36, gap=23.5), ["steel", "concrete", "banana"]):
        d.rect(x, y, w, h, t, stroke="neutral", sw="thick", size="body", id="e_" + t)
    d.text("**Separate, discrete entities**\n**with no inherent relationship.**", 102, 263, size="caption", color="primary")

    # ---- middle: mapping arrow (anchors pass through the midpoints of consecutive waypoints)
    d.text("**Mapping & Training**\n**Process**", 268, 99, size="subheading", color="primary")
    d.flex_arrow([(186, 149), (220, 124), (260, 140), (310, 160), (347, 140)], width=14, end_width=16, end_size=6,
                 fill="primary")
    d.text("**Assign to vectors &**\n**Train to reflect**\n**relationships**", 265, 190, size="caption", color="primary")

    # ---- panel 2: vector space
    d.panel(343, 9, 264, 275, "2. Continuous Vector Space (Output)", header_h=34, header_fill="neutral",
            header_opacity=55, header_color="primary", title_size="heading", stroke="neutral", sw="thick", id="p2")
    d.arrow([(375, 235), (375, 58)], color="neutral", sw="normal", head="block", head_size=5)   # Dimension 2 axis
    d.arrow([(362, 223), (562, 223)], color="neutral", sw="normal", head="block", head_size=5)  # Dimension 1 axis
    d.text("Dimension 2", 365, 144, size="axis", rotation=-90)
    d.text("Dimension 1", 465, 232, size="axis")
    d.circle(452, 112, 42, fill="none", stroke="neutral", sw="thick", dashed=True, dash="5 4", id="cluster")
    d.circle(375, 223, 1, fill="none", stroke="none", id="origin")            # invisible anchor for the vectors
    for name, (cx, cy) in {"steel": (429, 112), "concrete": (441, 114), "banana": (510, 195)}.items():
        d.dot(cx, cy, 4, fill="primary", stroke="primary", id="pt_" + name)
        d.edge([], src="origin", tgt="pt_" + name, color="primary", sw="thick", head_size=6)
    d.text("steel", 428, 100, size="label"); d.text("concrete", 469, 119, size="label"); d.text("banana", 525, 209, size="label")
    d.text("**Similar entities**\n**have similar vectors**\n**(close together)**", 550, 72, size="note", color="primary")
    d.edge([(523, 93)], tgt="cluster", color="primary", sw="normal", head_size=5)
    d.text("**Dissimilar entity**\n**is far away**", 558, 164, size="note", color="neutral")
    d.edge([(534, 178)], tgt="pt_banana", color="neutral", sw="normal", head_size=5)
    d.text("**Vectors in continuous space reflect**\n**meaningful relationships.**", 477, 263, size="caption", color="primary")


if __name__ == "__main__":
    run(layout, (616, 295), THEME, "03_vector_space_plot")
```

## Mode A, tier 4 — z-order and scientific geometry (excerpt of `04_complex_manifold.py`)

```python
THEME = {"colors": {"chunk_b": "#5b8c4a", "cluster_d": "#c2a27a"},
         "opacity": {"tint": 18, "beam": 28, "soft": 35, "chunk_c": 75, "faded": 35}, ...}
d.text('<span style="font-variant: small-caps">Visualizing the Manifold Hypothesis …</span>', 704, 30,
       w=1200, size="title", font="serif", raw=True)
d.rect(35, 57, 665, 538, rounded=12, sw="thick", id="panelA")
for p in ([(330, 110), (330, 410)], [(330, 410), (152, 465)], [(330, 410), (678, 505)]):   # 1 back cube edges
    d.line(p, color="neutral", sw="thin")
cube = [(152, 165), (330, 110), (678, 165), (678, 505), (340, 590), (152, 465)]
pts = d.scatter_in_polygon(cube, 190, keepout=[(40, 120, 218, 192), ...], min_dist=12, seed=7)
with d.group("points_behind"):                                                           # 2 points behind
    for x, y in pts[::2]: d.dot(x, y, 4.5, fill="neutral", stroke="text", stroke_opacity=25)
d.surface_mesh(back=[(172, 345), (240, 240), (330, 185), (430, 200), (510, 255), (548, 320)],   # 3 surface
               front=[(176, 352), (240, 420), (325, 495), (410, 470), (490, 385), (550, 326)],
               nu=30, nv=14, bulge=38, fill="secondary", fill_opacity="tint", line="primary")
d.polygon([(143, 203), (143, 307), (282, 286), (280, 276)], fill="secondary", fill_opacity="beam")  # beam
d.image_crop((49, 199, 143, 309), border="text")                                         # photo
loop = [(300, 272), (318, 250), (380, 252), (455, 288), (470, 312), (400, 330), (372, 356), (330, 322), (312, 290), (300, 272)]
d.line(loop, color="primary", sw=3, route="curved")                                      # closed curved loop
d.star(289, 281, 34, fill="secondary", id="star_A"); d.star(491, 305, 34, fill="chunk_b", id="star_B")
d.edge([], src="star_A", tgt="star_B", arrow=None, dashed=True)                          # attached distance
with d.group("points_front"):                                                            # 4 points in front
    for x, y in pts[1::2]: d.dot(x, y, 4.5, fill="neutral", stroke="text", stroke_opacity=25)
for p in ([(152, 165), (152, 465)], [(152, 165), (330, 110)], ...): d.line(p, sw="normal")  # 5 front edges
d.text("{secondary|**CHUNK A:**} Sound\nConcrete Pavement\n(3,072-D Vector)", 128, 160)       # 6 text last
arr = dict(route="curved", sw="normal", head_size=7)
d.arrow([(205, 150), (275, 160), (281, 265)], **arr)          # middle point = curve CONTROL point
d.callout(455, 475, 235, 100, "**Topological Mismatch:**\nLinear distance metrics often\ncut through …",
          tip=(444, 402), base_at=497, fill="neutral", fill_opacity="soft", size="label")
arc_y = lambda x: 270 + (0.0020 if x < 1042 else 0.00247) * (x - 1042) ** 2
d.line([(742, 465)] + [(x, arc_y(x)) for x in range(770, 1340, 30)] + [(1344, 465)],   # sample densely to
       color="secondary", sw=3.5, route="curved")                                        # pin a curve to a function
for x, y in d.scatter_along(arc_y, 750, 905, 38, spread=26, min_dist=10.5, seed=1): d.dot(x, y, 5.5)
d.text("Figure 1: …", 35, 692, w=1360, h=130, anchor="w", size="caption", font="serif", wrap=True,
       extra={"align": "left"})                                                          # wrapped caption
```

---
## Mode B, process passage — `A_methods_pipeline/` (complete)

`passage.md`:
> # Methods — RAG framework for pavement inspection reports
> 
> We propose a retrieval-augmented generation (RAG) framework for answering engineering questions over
> pavement inspection reports. In an offline indexing stage, scanned reports are converted to text through
> OCR, segmented into semantically coherent chunks, and encoded with a 3,072-dimensional embedding model;
> the resulting vectors are stored in a vector database together with metadata such as route, milepost,
> and inspection year. At query time, a practitioner's question is embedded with the same model, and the
> top-k most similar chunks are retrieved and re-ranked by a cross-encoder. The re-ranked context is
> inserted into a structured prompt, and a large language model generates an answer with citations to the
> source chunks. Finally, pavement engineers review each answer for factual accuracy and usefulness; their
> ratings are logged and used to tune the chunk size, the value of k, and the prompt template, closing the
> loop between system output and expert judgment.

`build.py`:
```python
"""Prototypes for passage A (methods: RAG pipeline). Run: python ../../scripts/prototype.py ."""
from figlib import *

INFERRED = []
ALLOWED_TERMS = ["layer", "representation", "retrieval", "evaluation", "data", "parameter", "tuning",
                 "practitioner", "online", "answering", "database", "human", "loop", "ingest"]

HL = style(DARK, bold=False)


def v1(d):
    """Swimlane pipeline: offline indexing lane above, online answering lane below, feedback loop."""
    lane(d, 20, 20, 1060, 175, "Offline indexing")
    lane(d, 20, 215, 1060, 170, "Online answering")
    X = [x for x, _, _, _ in d.row(80, 0, 6, 140, 60, gap=30)]
    off = chain(d, ["Inspection reports\n(scanned)", "OCR\nto text", "Semantic\nchunking",
                    "Embedding model\n(3,072-D)", "Vector database"], 80, 78, 140, 60, gap=30,
                shapes=["document", None, None, None, "cylinder"], ids=["o_rep", "o_ocr", "o_chk", "o_emb", "o_db"])
    d.text("*+ route · milepost · year*", X[4] + 64, 154, anchor="e", size="small", color="primary")
    d.rect(X[5], 78, 140, 60, "**Parameter tuning**\nchunk size · k · prompt", id="tune",
           **style(SOFT, dashed=True, size="label"))
    on = chain(d, ["Practitioner\nquestion", "Query\nembedding", "Retrieve top-k\nsimilar chunks", "Cross-encoder\nre-ranking",
                   "Prompt + LLM\ncited answer", "**Engineer review**\naccuracy · usefulness"], 80, 270, 140, 60, gap=30,
               styles=[SOFT] * 5 + [HL], ids=["n_q", "n_emb", "n_topk", "n_rr", "n_llm", "n_rev"])
    d.text("*same embedding model*", X[1] + 70, 346, size="small", color="secondary")
    d.edge([(X[4] + 70, 205), (X[2] + 70, 205)], src="o_db", tgt="n_topk", color="primary", sw="thick",
           exit=(.5, 1), entry=(.5, 0), label="*retrieve*", label_size="small")
    d.edge([], src="n_rev", tgt="tune", color="secondary", sw="thick", dashed=True, exit=(.5, 0), entry=(.5, 1), label="ratings")
    d.edge([(X[5] + 70, 50), (X[2] + 70, 50)], src="tune", tgt="o_chk", color="secondary", sw="thick", dashed=True,
           exit=(.5, 0), entry=(.5, 0))
    d.text("*closes the loop between system output and expert judgment*", (X[2] + X[5]) / 2 + 70, 38, size="small", color="secondary")


def v2(d):
    """Layered architecture: five layers, flow downward, tuning feedback on the right."""
    spec = [("Data\nlayer", ["Scanned inspection\nreports", "OCR\nto text", "Metadata\nroute · milepost · year"]),
            ("Representation\nlayer", ["Semantic\nchunks", "Embeddings\n(3,072-D)", "Vector\ndatabase"]),
            ("Retrieval\nlayer", ["Query\nembedding", "Retrieve top-k\nsimilar chunks", "Cross-encoder\nre-ranking"]),
            ("Generation\nlayer", ["Structured\nprompt", "Large language\nmodel", "Answer with\ncitations"]),
            ("Evaluation\nlayer", ["**Engineer review**\naccuracy · usefulness", "Ratings\nlog", "Parameter\ntuning"])]
    ids, boxes = layers(d, 40, 20, 940, spec, styles={2: SOFT, 3: SOFT})
    d.get(ids[(4, 0)])["style"].update(fillColor=d.theme.color("primary"), fontColor=d.theme.color("background"))
    yb = boxes[4][1] + boxes[4][3] / 2; yr = boxes[1][1] + boxes[1][3] / 2
    d.edge([(980, yb), (1015, yb), (1015, yr), (980, yr)], color="secondary", sw="thick", dashed=True)
    d.text("{secondary|*tune chunk size · k · prompt*}", 1032, (yb + yr) / 2, rotation=-90, size="label")


def v3(d):
    """Numbered cycle around a human-in-the-loop hub; closing arrow = tuning feedback."""
    labels = ["Ingest & OCR\nscanned reports", "Semantic\nchunking", "Embed chunks\n(3,072-D)", "Vector index\n+ metadata",
              "Embed question,\nretrieve top-k", "Cross-encoder\nre-ranking", "LLM answer\nwith citations", "**Engineer**\n**review**"]
    cycle(d, labels, 470, 320, 330, 240, styles=[NODE] * 4 + [SOFT] * 3 + [HL])
    d.text("{secondary|*tune chunk size · k · prompt*}", 245, 58, size="label")
    d.circle(470, 320, 108, "**Human-in-the-loop RAG**\nfor pavement\ninspection reports", fill="primary", stroke="primary",
             color="background", size="subheading")
    legend(d, 220, 648, [(NODE, "Offline indexing"), (SOFT, "Online answering"), (HL, "Expert judgment")])


VARIANTS = [
    dict(key="v1", name="swimlane_pipeline", size=(1100, 400), build=v1,
         about="Offline and online stages as two lanes; retrieval and the tuning loop drawn as routed connectors.",
         caption="Retrieval-augmented generation framework for pavement inspection reports: offline indexing (top) and online answering with engineer review and parameter tuning (bottom)."),
    dict(key="v2", name="layered_architecture", size=(1060, 600), build=v2,
         about="Five system layers stacked top to bottom with their components; tuning feedback on the side.",
         caption="Layered view of the proposed RAG framework, from scanned reports to expert evaluation; engineer ratings tune chunk size, k and the prompt template."),
    dict(key="v3", name="numbered_cycle", size=(940, 680), build=v3,
         about="Eight stages around a human-in-the-loop hub; offline, online and expert stages styled differently.",
         caption="The RAG workflow as a closed loop: engineer review of cited answers feeds back into chunking, retrieval depth and prompting."),
]
```
Result: `prototype` reports 0/0/0 for all three; captions and `about` lines appear on the sheet.

## Mode B, equation passage — `D_equation/` (passage + v1)

`passage.md`:
> # Equation — hybrid relevance score
> 
> Each candidate chunk $d$ is scored against the query $q$ with a hybrid relevance function
> $$s(q,d) = \lambda\,\mathrm{sim}(\mathbf{q},\mathbf{d}) + (1-\lambda)\,\mathrm{BM25}(q,d),$$
> where $\mathrm{sim}(\mathbf{q},\mathbf{d}) = \frac{\mathbf{q}\cdot\mathbf{d}}{\lVert\mathbf{q}\rVert\,\lVert\mathbf{d}\rVert}$
> is the cosine similarity between the 3,072-dimensional embeddings of the query and the chunk,
> $\mathrm{BM25}(q,d)$ is a lexical matching score normalized to $[0,1]$, and $\lambda \in [0,1]$ controls
> the balance between semantic and lexical evidence. Setting $\lambda = 1$ recovers pure dense retrieval,
> whereas $\lambda = 0$ reduces to keyword search; in our experiments $\lambda = 0.7$ gave the best answer
> accuracy. The top-$k$ chunks ranked by $s(q,d)$ are passed to the re-ranker.

```python
"""Prototypes for passage D (equation with explanation). Run: python ../../scripts/prototype.py ."""
import math
from figlib import *
from drawio_kit import measure_math


SIM = r"\mathrm{sim}(\mathbf{q},\mathbf{d})=\frac{\mathbf{q}\cdot\mathbf{d}}{\lVert\mathbf{q}\rVert\,\lVert\mathbf{d}\rVert}"


def v1(d):
    """Annotated equation: each term its own LaTeX label, color-coded, bracketed callouts, definition strip."""
    terms = [(r"s(q,d)", "primary"), (r"=", "text"), (r"\lambda", "secondary"),
             (r"\,\mathrm{sim}(\mathbf{q},\mathbf{d})", "primary"), (r"+", "text"), (r"(1-\lambda)", "secondary"),
             (r"\,\mathrm{BM25}(q,d)", "text")]
    annotated_equation(d, terms, 550, 205,
        notes_above=[(2, "secondary", "**Semantic weight λ** (0 to 1)\nλ = 1 → pure dense retrieval\nλ = 0.7 → best answer accuracy"),
                     (5, "secondary", "**Lexical weight 1 − λ**\nλ = 0 → keyword search")],
        notes_below=[(0, "primary", "**Hybrid relevance score**\nof chunk *d* for query *q*;\ntop-*k* go to the re-ranker"),
                     (3, "primary", "**Cosine similarity** of the\n3,072-D query and chunk\nembeddings (semantic evidence)"),
                     (6, "text", "**BM25 lexical matching**\nscore, normalized to [0, 1]\n(lexical evidence)")])
    d.rect(40, 425, 1020, 60, fill="secondary", fill_opacity="wash", stroke="neutral", sw="thin", rounded=10)
    d.text("**where**", 70, 455, anchor="w", size="label", color="primary")
    d.equation(SIM, 140, 455, anchor="w", size="eq_small", color="primary")
    d.text("is the cosine similarity between the embeddings of the query and the chunk.",
           140 + measure_math(SIM, d.theme.size("eq_small"))[0] + 24, 455, anchor="w", size="body")
# v2 computation_graph: Query/Chunk nodes → embedding & BM25 boxes → cosine / normalized-score boxes
#   (small d.equation inside) → ×λ and ×(1−λ) operator circles → "+" circle → DARK s(q,d) result;
#   λ∈[0,1] as a dashed tinted side box feeding both operators; orthogonal edges from operators.
# v3 intuition_glossary: angle θ between vectors q and d (invisible anchors + attached edges + arc polygon),
#   a continuum() for λ = 0 (keyword) … 0.7 (best) … 1 (dense), and a table() symbol | meaning | range.
INFERRED = [
    "v3: range [-1, 1] for cosine similarity is a mathematical property, not stated in the passage",
    "v3: 'angle between embeddings' (cos theta) is an explanatory interpretation of cosine similarity",
]
LINT_IGNORE = ["uneven gaps"]   # v1 callouts are aligned to their terms, not evenly spaced
ALLOWED_TERMS = ["path", "paths", "rank", "tokenize", "weight", "symbol", "meaning", "range", "angle", "balancing",
                 "kinds", "tests", "normalized", "semantic", "lexical", "evidence", "model"]
VARIANTS = [
    dict(key="v1", name="annotated_equation", size=(1100, 500), build=v1,
         about="Each term is its own LaTeX label, color-coded, with bracketed callouts; definition strip below.",
         caption="Hybrid relevance score: a lambda-weighted combination of embedding cosine similarity and normalized BM25."),
    dict(key="v2", name="computation_graph", size=(1120, 470), build=v2, ...),
    dict(key="v3", name="intuition_glossary", size=(1100, 640), build=v3, ...),
]
```

## Mode B, active demonstration — matrix grid pattern (from `E_matrix_computation/` v1)

```python
v_data = [["0.72", "0.00", "0.65", "0.00", "0.00"], ["0.55", "0.00", "0.58", "0.00", "0.00"], ...]   # 5 words × 5 docs
target_r, target_c = 1, 2                                # the cell whose dot product is traced
cell_w, cell_h, gx, gy = 36, 26, 105, 115
for r, row in enumerate(v_data):                         # populated V matrix, sparse zeros muted
    for c, val in enumerate(row):
        x, y = gx + c * cell_w, gy + r * cell_h
        if (r, c) == (target_r, target_c):               # active cell, highlighted role
            d.rect(x, y, cell_w, cell_h, f"**{val}**", fill="calc_light", stroke="calc_highlight", sw="thick", size="small")
        elif val == "0.00":
            d.rect(x, y, cell_w, cell_h, val, fill="sparse_zero", stroke="panel_border", sw="hairline", size="small", color="neutral")
        else:
            d.rect(x, y, cell_w, cell_h, val, fill="v_light", stroke="v_matrix", sw="thin", size="small", color="v_matrix")
# then W (5×2) and H (2×5) grids with row i / column j tinted, "≈" and "×" operators as equations,
# and a callout box tracing V_ij ≈ Σ_r W_ir H_rj with the actual numbers.
INFERRED = ["v1: numerical cell values for V, W, and H are concrete pedagogical instantiations", ...]
```
Comparison example INFERRED list (how interpretations are disclosed):
```python
INFERRED = ["v1: Classical ML 'Cost' rating (2 of 3, 'moderate') — the passage does not state ML cost",
            "v1: ordinal ratings (1-3 dots) are an interpretation of the passage's qualitative wording",
            "v2: 'Best fit when' statements are derived from the closing sentence",
            "v3: bubble sizes for rule-based and classical ML (only 'LLM = highest computational cost' is stated)",
            "v3: 'trade-off frontier' and 'ideal' corner are interpretive annotations"]
```

---
## Mode C — three worked enhancements

| Case | Origin → route | Target (from the interview) | Readiness |
|---|---|---|---|
| 1 BERT vs GPT (`test_fig1`) | mode A → rebuild (`build_enhanced.py`) | Elsevier 1.5-col (5.51 in, ≥ 7 pt), grayscale-safe, Helvetica | 93 → 100 |
| 2 hybrid score equation | mode B v1 → rebuild | IEEE double col (7.16 in, ≥ 8 pt), grayscale-safe, Times, paper notation | 48 → 100 |
| 3 NLP overview (hand-made, no build script) | edit (`drawio_doc` + `enhance --map`) | Elsevier double col (7.48 in, ≥ 7 pt), color, CVD-safe | 24 → 100 |

**Case 1 — message-first edits.** Brief: purpose = comparison; takeaway "BERT predicts a masked token
from both sides; GPT predicts the next token from the left only"; emphasis `[MASK] | Output:`; density =
shorten, explanations → caption; caption written from the paper. Changes: white page; in-figure title
→ caption; panel titles "(a) Auto-encoding (BERT)" / "(b) Autoregressive (GPT)"; the two predicted
tokens styled identically (dashed secondary outline) + legend, replacing decorative direction glyphs;
"Best for …" lines → caption; panel outlines thickened to ≥ 0.5 pt; passes: 3 sizes → 1 level, page fitted.
Accepted warning: "categories dropped from" (the faded ghost token was removed on purpose).
Caption: *Two pre-training objectives for Transformer language models. (a) Auto-encoding (BERT): an
encoder sees bidirectional context and reconstructs a masked token; suited to understanding and
classification. (b) Autoregressive (GPT): a decoder reads tokens left to right and predicts the next
one; suited to generation.*

**Case 2 — print-size reflow.** The 1100-px canvas would print labels at ~6 pt → canvas 760 px so
labels reach ≥ 8 pt at 7.16 in; callouts shortened (explanations → caption); λ moved from Unicode to
inline LaTeX for consistent notation; main equation 30 → 24 px (~1.6 × label size in print); Times New
Roman; notation brief "bold vectors (q, d), upright sim and BM25"; attach pass fixed 5 free edge ends;
math on (8 LaTeX labels); faithfulness re-checked; accepted "uneven gaps" (term-aligned callouts).

**Case 3 — deliberate palette consolidation (edit route).** Removed in-figure title (→ caption),
decorative footer and a placeholder copied from the source; ~20 per-panel pastels mapped to 3 roles at
fixed opacities, applied with `T enhance FIG --colors --map "#hex=role@opacity" …`:
```
#f4f7fa=background  #dbe9f3=background  #eef5f8=neutral@8   #9fb8cc=neutral    #d7ecd6=background
#8fbf8c=neutral     #e3e6f3=secondary@22 #eef0f7=secondary@7 #aab3d3=secondary  #dfe6f6=secondary@30
#9aa9d4=secondary   #ece2f4=secondary@30 #b49ac6=secondary  #f1e8f5=secondary@10 #f4ecd8=primary@15
#f8f4ea=primary@5   #cdbd94=primary     #f2e4c0=primary@8   #c9ad6a=primary    #f5e8c8=primary@15
#f7dfb5=primary@28  #d2a85c=primary     #1f2a36=text        #6b7785=text       #c5ced8=neutral  #8fb3cc=secondary
```
NLP = neutral (white tiles, gray outlines), NLU = secondary tints, NLG = primary tints. Then tuned until
NLI relations separate by lightness under grayscale/CVD (Entailment secondary 10 %, Contradiction primary
40 %, Neutral white); NLP header white with gray outline; NLG tiles primary 8 % (was 15 %); light-gray
canvas → white; two remaining sizes (15.5-px headings, 26-px icons) added as theme roles; long labels
re-broken (same words) to fit at 7 pt; passes: 105 colors snapped, 7 sizes → 5 levels, 6 strokes
snapped, 6 edge ends attached. Accepted: "dense; move explanations", "categories dropped from" (6 → 4
fill categories, intended), "under protanopia" (NLU/NLG panels also identified by position and header
text). An earlier color pass had flattened these tints to white — the lost-category audit now catches that.
