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


def v2(d):
    """Computation graph: how the score is assembled from two evidence paths."""
    d.rect(30, 120, 130, 54, "Query *q*", id="q", **NODE)
    d.rect(30, 290, 130, 54, "Chunk *d*", id="dd", **NODE)
    d.rect(230, 60, 190, 60, "Embedding model\n(3,072-D)", id="emb", **SOFT)
    d.rect(230, 340, 190, 60, "Tokenize +\nBM25 scoring", id="bm", **NODE)
    d.rect(480, 50, 230, 80, "", id="cos", **SOFT)
    d.text("**Cosine similarity**", 595, 66, size="label", color="primary")
    d.equation(r"\frac{\mathbf{q}\cdot\mathbf{d}}{\lVert\mathbf{q}\rVert\,\lVert\mathbf{d}\rVert}", 595, 102, size="eq_small", color="primary")
    d.rect(480, 335, 230, 70, "", id="bmn", **NODE)
    d.text("**Normalized lexical score**", 595, 352, size="label")
    d.equation(r"\mathrm{BM25}(q,d)\in[0,1]", 595, 383, size="eq_small")
    d.circle(800, 90, 28, "", id="m1", fill="background", stroke="secondary", sw="thick")
    d.equation(r"\times\lambda", 800, 90, size="eq_small", color="secondary")
    d.circle(800, 370, 36, "", id="m2", fill="background", stroke="secondary", sw="thick")
    d.equation(r"\times(1-\lambda)", 800, 370, size="label", color="secondary")
    d.circle(890, 230, 30, "", id="plus", fill="primary", stroke="primary")
    d.equation(r"+", 890, 230, size="eq_term", color="background")
    d.rect(960, 195, 140, 70, "", id="s", **DARK)
    d.equation(r"s(q,d)", 1030, 220, size="eq_term", color="background")
    d.text("{background|rank → top-*k*}", 1030, 248, size="small")
    d.rect(620, 200, 170, 60, "", id="lam", fill="secondary", fill_opacity="tint", stroke="secondary", dashed=True, rounded=True)
    d.equation(r"\lambda\in[0,1]", 705, 220, size="eq_small", color="secondary")
    d.text("*0.7 best in our tests*", 705, 246, size="small", color="secondary")
    for a, b, ex, en in [("q", "emb", (1, .5), (0, .5)), ("dd", "emb", (1, .2), (0, .8)), ("q", "bm", (1, .8), (0, .2)),
                         ("dd", "bm", (1, .5), (0, .5)), ("emb", "cos", (1, .5), (0, .5)), ("bm", "bmn", (1, .5), (0, .5)),
                         ("cos", "m1", (1, .5), (0, .5)), ("bmn", "m2", (1, .5), (0, .5)), ("m1", "plus", (1, .5), (.5, 0)),
                         ("m2", "plus", (1, .5), (.5, 1)), ("plus", "s", (1, .5), (0, .5))]:
        d.edge([], src=a, tgt=b, color="primary", sw="thick", exit=ex, entry=en, route="orthogonal" if a in ("m1", "m2") else "straight")
    d.edge([], src="lam", tgt="m1", color="secondary", sw="normal", dashed=True, exit=(.85, 0), entry=(.5, 1))
    d.edge([], src="lam", tgt="m2", color="secondary", sw="normal", dashed=True, exit=(.85, 1), entry=(.5, 0))
    d.text("{secondary|**semantic path**}", 325, 30, size="label")
    d.text("**lexical path**", 325, 430, size="label")

def v3(d):
    """Intuition + glossary: vector angle for cosine similarity, λ continuum, symbol table."""
    # left: geometry
    d.rect(20, 20, 420, 330, fill="secondary", fill_opacity="wash", stroke="neutral", sw="thin", rounded=10)
    d.text("**Dense evidence: angle between embeddings**", 230, 44, size="label", color="primary")
    ox, oy = 90, 300
    d.circle(ox, oy, 1, fill="none", stroke="none", id="o")
    d.circle(380, 120, 1, fill="none", stroke="none", id="qt")
    d.circle(400, 250, 1, fill="none", stroke="none", id="dt")
    d.edge([], src="o", tgt="qt", color="primary", sw="heavy")
    d.edge([], src="o", tgt="dt", color="secondary", sw="heavy")
    d.equation(r"\mathbf{q}", 395, 108, size="eq_term", color="primary")
    d.equation(r"\mathbf{d}", 415, 252, size="eq_term", color="secondary")
    a1, a2 = math.atan2(120 - oy, 380 - ox), math.atan2(250 - oy, 400 - ox)
    arc = [(ox + 110 * math.cos(a1 + (a2 - a1) * t / 20), oy + 110 * math.sin(a1 + (a2 - a1) * t / 20)) for t in range(21)]
    d.polygon(arc, closed=False, stroke="text", fill=None, sw="normal")
    d.equation(r"\theta", ox + 130, oy - 70, size="eq_term")
    d.equation(r"\mathrm{sim}(\mathbf{q},\mathbf{d})=\cos\theta", 230, 330, size="eq_small", color="primary")
    # right: lambda continuum
    d.rect(470, 20, 610, 330, fill="background", stroke="neutral", sw="thin", rounded=10)
    d.text("**Balancing semantic and lexical evidence**", 775, 44, size="label", color="primary")
    d.equation(r"s(q,d)=\lambda\,\mathrm{sim}(\mathbf{q},\mathbf{d})+(1-\lambda)\,\mathrm{BM25}(q,d)", 775, 100, size="eq_term")
    x0, x1, yb = 520, 1030, 210
    d.rect(x0, yb - 8, x1 - x0, 16, fill="neutral", gradient="secondary", gradient_dir="east", stroke="none", rounded=8)
    for v, lab in ((0, "keyword search"), (1, "pure dense retrieval")):
        x = x0 + v * (x1 - x0)
        d.equation(rf"\lambda={v}", x, yb + 34, size="eq_small", color="primary")
        d.text(lab, x, yb + 62, size="small")
    xb = x0 + 0.7 * (x1 - x0)
    d.shape("triangle_down", xb - 11, yb - 36, 22, 18, fill="primary", stroke="primary")
    d.text("**λ = 0.7** best answer accuracy", xb, yb - 50, size="small", color="primary")
    d.text("lexical evidence ← → semantic evidence", 775, yb + 110, size="small", color="neutral")
    # bottom: symbol table
    rows = [(r"s(q,d)", "hybrid relevance score; top-k chunks go to the re-ranker", ""),
            (r"\mathrm{sim}(\mathbf{q},\mathbf{d})", "cosine similarity of 3,072-D query and chunk embeddings", r"[-1,1]"),
            (r"\mathrm{BM25}(q,d)", "lexical (keyword) matching score, normalized", r"[0,1]"),
            (r"\lambda", "weight on semantic vs. lexical evidence", r"[0,1]")]
    ty, rh = 370, 52
    for j, (h, w) in enumerate((("Symbol", 220), ("Meaning", 700), ("Range", 140))):
        xs = [20, 240, 940][j]
        d.rect(xs, ty, w, 36, f"**{h}**", fill="primary", stroke="background", color="background", size="label")
    for i, (sym, mean, rng) in enumerate(rows):
        y = ty + 36 + i * rh
        d.rect(20, y, 1060, rh, fill="secondary" if i % 2 == 0 else "background", fill_opacity="wash" if i % 2 == 0 else None,
               stroke="neutral", sw="thin")
        d.equation(sym, 130, y + rh / 2, size="eq_small", color="primary")
        d.text(mean, 260, y + rh / 2, anchor="w", size="body")
        if rng:
            d.equation(rng, 1010, y + rh / 2, size="eq_small")


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
    dict(key="v2", name="computation_graph", size=(1120, 470), build=v2,
         about="How the score is assembled: semantic and lexical paths, weighting by lambda, sum, ranking.",
         caption="Computation of the hybrid score s(q, d) from dense (embedding) and lexical (BM25) evidence."),
    dict(key="v3", name="intuition_glossary", size=(1100, 640), build=v3,
         about="Geometric meaning of cosine similarity, the lambda continuum with the best setting, and a symbol table.",
         caption="Interpreting the hybrid score: lambda moves retrieval between keyword search (0) and pure dense retrieval (1); 0.7 gave the best accuracy."),
]
