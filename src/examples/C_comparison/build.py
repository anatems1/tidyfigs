"""Prototypes for passage C (comparison of three approaches). Run: python ../../scripts/prototype.py ."""
import math
from figlib import *

METHODS = [("Rule-based", "keyword dictionaries +\nexpert heuristics"),
           ("Classical ML", "e.g., SVM on\nTF-IDF features"),
           ("LLM-based", "prompting or\nfine-tuning")]
# ratings: 3 = most favourable; words come from the text
CRIT = ["Labeled data\nrequired", "Interpretability", "Generalization", "Cost"]
R = [[(3, "none"), (3, "full"), (1, "poor on unseen terms"), (2, "costly to maintain")],
     [(1, "moderate"), (2, "partial (feature weights)"), (2, "within a single agency"), (2, "moderate")],
     [(2, "little task-specific"), (1, "least"), (3, "across agencies & styles"), (1, "highest compute")]]


def v1(d):
    """Comparison matrix with 3-dot ratings and the source wording under each rating."""
    x0, w0, cw, hh, rh = 20, 220, 190, 64, 96
    d.rect(x0, 20, w0, hh, "**Approach**", fill="primary", stroke="background", color="background", size="subheading")
    for j, c in enumerate(CRIT):
        d.rect(x0 + w0 + j * cw, 20, cw, hh, f"**{c}**", fill="primary", stroke="background", color="background", size="subheading")
    for i, (m, desc) in enumerate(METHODS):
        y = 20 + hh + i * rh
        band = "secondary" if i % 2 == 0 else "background"
        d.rect(x0, y, w0 + 4 * cw, rh, fill=band, fill_opacity="wash" if i % 2 == 0 else None, stroke="neutral", sw="thin")
        d.text(f"**{m}**", x0 + 16, y + 30, anchor="w", size="subheading", color="primary")
        d.text(f"*{desc}*", x0 + 16, y + 64, anchor="w", size="label")
        for j, (n, word) in enumerate(R[i]):
            cx = x0 + w0 + j * cw + cw / 2
            rating_dots(d, cx, y + 36, n)
            d.text(word, cx, y + 68, size="small", w=cw - 16, wrap=True)
    yb = 20 + hh + 3 * rh + 18
    rating_dots(d, 40, yb + 12, 3, r=5, gap=14); d.text("most favourable", 66, yb + 12, anchor="w", size="small")
    rating_dots(d, 210, yb + 12, 1, r=5, gap=14); d.text("least favourable", 236, yb + 12, anchor="w", size="small")
    d.rect(400, yb - 4, 580, 34, "**No single approach dominates:** choose by data availability, auditability, and budget.",
           fill="secondary", fill_opacity="tint", stroke="secondary", rounded=17, size="label")

def v2(d):
    """Three cards: how it works, strengths, limitations, best fit; conclusion banner."""
    cards = [("Rule-based", "Keyword dictionaries and expert-defined heuristics.",
              ["No training data needed", "Fully interpretable"], ["Poor generalization to unseen terms", "Costly to maintain"],
              "need for auditability;\nno training data"),
             ("Classical ML", "Support vector machines trained on TF-IDF features.",
              ["Partial interpretability (feature weights)", "Generalizes within a single agency"], ["Needs moderate labeled data", "Vocabulary of a single agency"],
              "moderate labeled data within\na single agency"),
             ("LLM-based", "Prompting or fine-tuning a large language model.",
              ["Little task-specific labeled data", "Best generalization across agencies"], ["Least interpretable", "Highest computational cost"],
              "generalization across agencies;\ndeployment budget available")]
    for i, (name, how, pros, cons, fit) in enumerate(cards):
        x = 20 + i * 333
        w = 313
        with d.group(f"card{i}"):
            d.rect(x, 20, w, 390, fill="background", stroke="neutral", sw="thin", rounded=12, shadow=True)
            d.rect(x, 20, w, 54, f"**{name}**", fill="primary", stroke="primary", color="background", rounded=12, size="heading")
            d.text(f"*{how}*", x + 18, 104, anchor="w", w=w - 36, h=40, wrap=True, size="label")
            d.text("**Strengths**", x + 18, 150, anchor="w", size="body", color="secondary")
            for k, p in enumerate(pros):
                d.text(f"{{secondary|**+**}}  {p}", x + 18, 178 + k * 26, anchor="w", size="label")
            d.text("**Limitations**", x + 18, 250, anchor="w", size="body", color="primary")
            for k, c in enumerate(cons):
                d.text(f"{{primary|**–**}}  {c}", x + 18, 278 + k * 26, anchor="w", size="label")
            d.rect(x + 14, 326, w - 28, 70, f"**Best fit**\n{fit}", fill="secondary", fill_opacity="tint",
                   stroke="none", rounded=8, size="label")
    d.rect(20, 430, 979, 50, "**No single approach dominates** — the choice depends on data availability, the need for auditability, and deployment budget.",
           fill="primary", stroke="primary", color="background", rounded=25, size="body")

def v3(d):
    """Positioning chart: generalization (x) vs interpretability (y); bubble area = computational cost."""
    ox, oy, x1, y1 = 120, 500, 860, 60
    d.rect(ox, y1, x1 - ox, oy - y1, fill="neutral", fill_opacity="wash", stroke="none")
    d.text("{neutral|*ideal*}", x1 - 40, y1 + 80, size="small")
    d.star(x1 - 40, y1 + 48, 26, fill="background", stroke="neutral", dashed=True)
    d.arrow([(ox, oy), (x1 + 20, oy)], color="text", sw="normal")
    d.arrow([(ox, oy), (ox, y1 - 20)], color="text", sw="normal")
    d.text("**Generalization** across agencies and writing styles", (ox + x1) / 2, oy + 48, size="body")
    d.text("**Interpretability**", ox - 62, (oy + y1) / 2, rotation=-90, size="body")
    for t, x in (("poor", ox + 110), ("within a single agency", (ox + x1) / 2), ("across agencies", x1 - 110)):
        d.text(t, x, oy + 18, size="small", color="neutral")
    for t, y in (("least", oy - 70), ("partial", (oy + y1) / 2), ("full", y1 + 70)):
        d.text(t, ox - 30, y, size="small", color="neutral")
    d.line([(ox + 145, y1 + 35), (ox + 440, y1 + 157), (x1 - 65, oy - 115)], color="neutral", sw="thick",
           dashed=True, route="curved")     # middle point = control point (curve bows toward it)
    d.text("{neutral|*trade-off frontier*}", ox + 470, y1 + 150, anchor="w", size="small")
    pts = [("Rule-based", ox + 110, y1 + 70, 16, "no labeled data"), ("Classical ML", (ox + x1) / 2, (oy + y1) / 2, 26, "moderate labeled data"),
           ("LLM-based", x1 - 110, oy - 70, 50, "little labeled data")]
    for i, (name, x, y, r, lab) in enumerate(pts):
        d.circle(x, y, r, fill="secondary" if i < 2 else "primary", fill_opacity=60 if i < 2 else 85, stroke="primary", id=f"b{i}")
        if i == 0:
            d.text(f"**{name}**\n*{lab}*", x, y + r + 8, anchor="n", size="label")
        elif i == 1:
            d.text(f"**{name}**\n*{lab}*", x + r + 14, y + 12, anchor="w", size="label")
        else:
            d.text(f"**{name}**\n*{lab}*", x - r - 14, y, anchor="e", size="label")
    # legend
    lx, ly = 150, 598
    d.text("Bubble size = computational cost", lx, ly, anchor="w", size="small")
    for k, r in enumerate((8, 14, 22)):
        d.circle(lx + 250 + k * 50, ly, r, fill="secondary", fill_opacity=60, stroke="primary")
    d.text("low → highest", lx + 390, ly, anchor="w", size="small", color="neutral")


INFERRED = [
    "v1: Classical ML 'Cost' rating (2 of 3, 'moderate') — the passage does not state ML cost",
    "v1: ordinal ratings (1-3 dots) are an interpretation of the passage's qualitative wording",
    "v2: 'Best fit when' statements are derived from the closing sentence (data availability, auditability, budget)",
    "v3: bubble sizes for rule-based and classical ML (only 'LLM = highest computational cost' is stated)",
    "v3: 'trade-off frontier' and 'ideal' corner are interpretive annotations",
]
ALLOWED_TERMS = ["choose", "most", "none", "approach", "cost", "favourable", "ideal", "frontier", "bubble", "size", "low", "medium", "fit",
                 "strengths", "limitations", "maintenance", "upkeep", "terms", "styles", "tuning"]

VARIANTS = [
    dict(key="v1", name="rating_matrix", size=(1000, 440), build=v1,
         about="Approaches x criteria with 3-dot ratings and the passage's own wording under each rating.",
         caption="Comparison of rule-based, classical machine-learning and LLM-based approaches to distress identification from inspection text."),
    dict(key="v2", name="method_cards", size=(1020, 500), build=v2,
         about="One card per approach: how it works, strengths, limitations, best fit; conclusion banner.",
         caption="Strengths and limitations of three families of methods for automated pavement distress identification."),
    dict(key="v3", name="positioning_chart", size=(940, 630), build=v3,
         about="Generalization vs. interpretability, bubble size = computational cost, trade-off frontier.",
         caption="No approach dominates: interpretability decreases as generalization across agencies increases."),
]
