"""Prototypes for passage B (conceptual framework). Run: python ../../scripts/prototype.py ."""
import math
from figlib import *



def v1(d):
    """Causal columns: drivers -> mechanisms -> indicators -> decisions, moderators beneath."""
    cols = {"drv": 150, "mech": 425, "ind": 700, "dec": 975}
    for k, t in zip(cols, ["External drivers", "Distress mechanisms", "Condition indicators", "M&R decisions"]):
        pill(d, cols[k], 20, t, w=210)
    ys = [80, 150, 220, 290]
    drv = ["Traffic loading", "Temperature cycling", "Moisture infiltration", "Freeze–thaw action"]
    mech = ["**Fatigue (alligator) cracking**\n*load repetitions*", "**Rutting**\n*load + high temperature*",
            "**Thermal cracking**\n*low-temperature contraction*", "**Joint spalling**\n*moisture + freeze–thaw*"]
    for i, (a, b) in enumerate(zip(drv, mech)):
        d.rect(cols["drv"] - 95, ys[i], 190, 50, a, id=f"d{i}", **NODE)
        d.rect(cols["mech"] - 100, ys[i], 200, 50, b, id=f"m{i}", **dict(SOFT, size="label"))
    for a, b in [(0, 0), (0, 1), (1, 1), (1, 2), (2, 3), (3, 3)]:
        d.edge([], src=f"d{a}", tgt=f"m{b}", color="primary", sw="normal", exit=(1, .5), entry=(0, .5))
    d.rect(cols["mech"] - 110, 66, 220, 288, fill="none", stroke="secondary", sw="thin", dashed=True, rounded=10, id="mech_grp")
    d.rect(cols["ind"] - 95, 135, 190, 60, "**Pavement Condition**\n**Index (PCI)**", id="pci", **DARK)
    d.rect(cols["ind"] - 95, 225, 190, 60, "**International Roughness**\n**Index (IRI)**", id="iri", **DARK)
    d.rect(cols["ind"] - 110, 120, 220, 180, fill="none", stroke="primary", sw="thin", dashed=True, rounded=10, id="ind_grp")
    dec = ["Preventive treatment\n*e.g., crack sealing*", "Rehabilitation\n*e.g., overlay*", "Full reconstruction"]
    for i, t in enumerate(dec):
        d.rect(cols["dec"] - 95, 80 + i * 95, 190, 60, t, id=f"r{i}", **NODE)
    d.rect(cols["dec"] - 110, 66, 220, 288, fill="none", stroke="primary", sw="thin", dashed=True, rounded=10, id="dec_grp")
    d.edge([], src="mech_grp", tgt="ind_grp", color="primary", sw="heavy", exit=(1, .5), entry=(0, .5))
    d.text("*quantified by*", (cols["mech"] + 110 + cols["ind"] - 110) / 2, 196, anchor="s", size="small", color="primary")
    d.edge([], src="ind_grp", tgt="dec_grp", color="primary", sw="heavy", exit=(1, .5), entry=(0, .5))
    d.text("*inform*", (cols["ind"] + 110 + cols["dec"] - 110) / 2, 196, anchor="s", size="small", color="primary")
    d.arrow([(1112, 85), (1112, 335)], color="neutral", sw="heavy", head_size=6)
    d.text("*preventive → major rehabilitation*", 1132, 210, rotation=-90, size="small", color="neutral")
    d.rect(55, 400, 500, 64, "**Internal moderators** — material quality · construction practice", id="mod", **MUTED)
    d.edge([(445, 377)], src="mod", tgt="mech_grp", color="neutral", sw="thick", dashed=True, exit=(.78, 0), entry=(.5, 1))
    d.text("*moderate the structural response*", 455, 377, anchor="w", size="small", color="neutral")

def v2(d):
    """Stepped funnel: four stages narrowing top-to-bottom, chips inside, moderators to the side."""
    cx = 440
    stages = [("External drivers", ["Traffic loading", "Temperature cycling", "Moisture infiltration", "Freeze–thaw"], 840, "neutral", 18),
              ("Distress mechanisms", ["Fatigue cracking", "Rutting", "Thermal cracking", "Joint spalling"], 700, "secondary", 18),
              ("Condition indicators", ["PCI", "IRI"], 560, "secondary", 35),
              ("M&R decisions", ["Crack sealing", "Overlay", "Reconstruction"], 440, "primary", 100)]
    y = 20
    for i, (name, chips, w, col, op) in enumerate(stages):
        h = 116
        dark = op == 100
        d.rect(cx - w / 2, y, w, h, fill=col, fill_opacity=op, stroke=col, sw="normal", rounded=14, id=f"st{i}")
        d.text(f"**{name}**", cx, y + 22, size="subheading", color="background" if dark else "primary")
        cw = min(170, (w - 40 - 14 * (len(chips) - 1)) / len(chips))
        if len(chips) == 2:
            cw = 200
        total = cw * len(chips) + 14 * (len(chips) - 1)
        for j, (bx, by, bw, bh) in enumerate(d.row(cx - total / 2, y + 48, len(chips), cw, 46, gap=14)):
            d.rect(bx, by, bw, bh, chips[j], fill="background", stroke="primary" if not dark else "background",
                   rounded=23, size="body", id=f"c{i}{j}")
        if i < 3:
            d.shape("triangle_down", cx - 18, y + h + 6, 36, 18, fill="primary", stroke="primary")
        y += h + 30
    d.text("{background|*preventive → major rehabilitation*}", cx, 20 + 3 * 146 + 102, size="small")
    d.rect(860, 176, 165, 96, "**Moderators**\nmaterial quality\nconstruction practice", fill="neutral", fill_opacity="tint",
           stroke="neutral", dashed=True, rounded=True, size="label", id="mod")
    d.edge([], src="mod", tgt="st1", color="neutral", sw="thick", dashed=True, exit=(0, .5), entry=(1, .5))

def v3(d):
    """Concept map: pavement structure as the hub, labeled relations."""
    hub = (530, 260)
    d.ellipse(hub[0] - 100, hub[1] - 46, 200, 92, "**Pavement**\n**structure**", fill="primary", stroke="primary",
              color="background", size="subheading", id="hub")
    ys = [110, 220, 330, 440]
    for i, t in enumerate(["Traffic\nloading", "Temperature\ncycling", "Moisture\ninfiltration", "Freeze–thaw\naction"]):
        d.rect(60, ys[i] - 28, 150, 56, t, id=f"drv{i}", **NODE)
        d.edge([], src=f"drv{i}", tgt="hub", color="primary", sw="normal")
    d.text("*act on*", 300, 214, size="small", color="primary")
    for i, (t, x) in enumerate([("Material quality", 420), ("Construction\npractice", 640)]):
        d.rect(x - 85, 40, 170, 56, t, id=f"mod{i}", **MUTED)
        d.edge([], src=f"mod{i}", tgt="hub", color="neutral", sw="normal", dashed=True)
    d.text("*moderate*", 530, 150, size="small", color="neutral")
    mech = ["**Fatigue cracking**\n*load repetitions*", "**Rutting**\n*load + high T*",
            "**Thermal cracking**\n*low-T contraction*", "**Joint spalling**\n*moisture + freeze–thaw*"]
    for i, t in enumerate(mech):
        d.rect(840, ys[i] - 28, 180, 56, t, id=f"mech{i}", **dict(SOFT, size="label"))
        d.edge([], src="hub", tgt=f"mech{i}", color="secondary", sw="normal")
    d.text("{secondary|*manifests as*}", 750, 214, size="small")
    d.rect(825, 66, 210, 418, fill="none", stroke="secondary", sw="thin", dashed=True, rounded=12, id="mech_grp")
    d.rect(430, 470, 200, 56, "**PCI · IRI**\ncondition indicators", id="ind", **DARK)
    d.edge([(930, 498)], src="mech_grp", tgt="ind", color="primary", sw="thick", exit=(.5, 1), entry=(1, .5))
    d.text("*quantified by*", 780, 488, anchor="s", size="small", color="primary")
    d.rect(410, 570, 240, 56, "**M&R decisions**\n*crack sealing → reconstruction*", id="dec", **NODE)
    d.edge([], src="ind", tgt="dec", color="primary", sw="thick", exit=(.5, 1), entry=(.5, 0))
    d.text("*inform*", 545, 548, anchor="w", size="small", color="primary")


INFERRED = []
ALLOWED_TERMS = []

VARIANTS = [
    dict(key="v1", name="causal_columns", size=(1150, 500), build=v1,
         about="Drivers -> mechanisms -> indicators -> decisions, with the specific driver-mechanism links and moderators.",
         caption="Conceptual framework of pavement deterioration: external drivers act through distinct distress mechanisms, quantified by PCI and IRI, which inform maintenance and rehabilitation decisions."),
    dict(key="v2", name="stepped_funnel", size=(1040, 610), build=v2,
         about="Four stages narrowing top to bottom; compact overview without individual links.",
         caption="From drivers to decisions: the cumulative effect of distress mechanisms is quantified by condition indicators that inform treatment selection."),
    dict(key="v3", name="concept_map", size=(1060, 640), build=v3,
         about="Pavement structure as the hub with labeled relations (act on, moderate, manifests as, quantified by, inform).",
         caption="Concept map of pavement deterioration: traffic and environmental exposure act on the pavement structure, moderated by material quality and construction practice."),
]
