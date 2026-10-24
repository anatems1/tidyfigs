#!/usr/bin/env python3
"""
Tier 2 — three-column infographic with tiles, icons and mini flow diagrams (NLP / NLU / NLG), 1024x559.
Shows: per-panel tint roles, header+body panels, tiles as groups (box+icon+label) laid out with
fit_row() so gaps are identical, emoji icon placeholders, nested NLI box with branching connectors,
orthogonal routing with explicit waypoints, bullet lists, footer rule with centered label.
Tip: run with --scale 1.5 so small text is comfortable to edit.
"""
from _common import run

THEME = {
    "colors": {
        "canvas": "#f4f7fa", "ink": "#1f2a36", "muted": "#6b7785", "rule": "#c5ced8", "connector": "#8fb3cc",
        "nlp_head": "#dbe9f3", "nlp_body": "#eef5f8", "nlp_line": "#9fb8cc",
        "nlu_head": "#e3e6f3", "nlu_body": "#eef0f7", "nlu_line": "#aab3d3",
        "nlg_head": "#f4ecd8", "nlg_body": "#f8f4ea", "nlg_line": "#cdbd94",
        "tile_green": "#d7ecd6", "tile_green_line": "#8fbf8c", "tile_blue": "#dfe6f6", "tile_blue_line": "#9aa9d4",
        "tile_purple": "#ece2f4", "tile_purple_line": "#b49ac6", "tile_tan": "#f2e4c0", "tile_tan_line": "#c9ad6a",
        "nli_fill": "#f1e8f5", "contra": "#f7dfb5", "contra_line": "#d2a85c", "hyp": "#f5e8c8",
    },
    "sizes": {"title": 21, "heading": 15.5, "body": 13.5, "label": 13, "small": 11, "icon": 30, "icon_sm": 26, "icon_md": 28},
    "strokes": {"thin": 1.2, "normal": 1.5},
}


def tile(d, id, box, col, icon, label, icy, lcy, size="body"):
    x, y, w, h = box
    with d.group(id):
        d.rect(x, y, w, h, fill=f"tile_{col}", stroke=f"tile_{col}_line", sw="normal", rounded=6, id=id + "_box")
        d.icon(icon, x + w / 2, icy, size=d.theme.size("icon"))
        d.text(label, x + w / 2, lcy, size=size, color="ink")


def layout(d):
    d.background = "canvas"
    d.text("**FUNCTIONAL BREAKDOWN OF NATURAL LANGUAGE PROCESSING: NLP, NLU, NLI & NLG**", 512, 35,
           size="title", color="ink")
    cols = [("nlp", 33, 297, "**1. NATURAL LANGUAGE PROCESSING**\n**(NLP)** - Overarching Field", "🧠",
             "Field combining computer science, AI,\nand linguistics to enable interactions\nbetween computers and human language."),
            ("nlu", 364, 297, "**2. NATURAL LANGUAGE UNDERSTANDING**\n**(NLU)** - Intent & Semantics", "📋",
             "Subfield focused on machine understanding\nof text and speech, discerning meaning,\nintent, and relationships."),
            ("nlg", 695, 297, "**3. NATURAL LANGUAGE GENERATION**\n**(NLG)** - Creation & Output", "📝",
             "Process of producing coherent natural\nlanguage text or speech from structured\ndata or conceptual intent.")]
    for key, x, w, head, icon, desc in cols:
        d.rect(x, 65, w, 53, head, fill=f"{key}_head", stroke=f"{key}_line", rounded=6, size="heading", color="ink", id=f"{key}_head")
        d.rect(x, 125, w, 415, fill=f"{key}_body", stroke=f"{key}_line", rounded=6, shadow=True, id=f"{key}_body")
        d.icon(icon, x + 24, 160, size=d.theme.size("icon"))
        d.text(desc, x + 45, 160, anchor="w", size="label", color="ink")
    # connectors between panels (elbow from body up into next header)
    d.arrow([(346, 140), (346, 92), (363, 92)], color="connector", route="straight")
    d.arrow([(678, 140), (678, 92), (694, 92)], color="connector", route="straight")

    # --- NLP panel: two tile rows with equal gaps
    r1 = d.fit_row(43, 320, 198, 3, 102, gap=9)          # symmetric inside the 33..330 panel
    for box, (ic, lb, idn) in zip(r1, [("🗂️", "Information\nExtraction", "ie"), ("🔤", "Machine\nTranslation", "mt"),
                                       ("🔊", "Speech\nRecognition", "sr1")]):
        tile(d, "t_" + idn, box, "green", ic, lb, icy=232, lcy=276)
    r2 = d.row(43, 312, 2, r1[0][2], 108, gap=9)
    for box, (ic, lb, idn) in zip(r2, [("🎙️", "Speech\nRecognition", "sr2"), ("😊", "Sentiment\nAnalysis", "sa")]):
        tile(d, "t_" + idn, box, "green", ic, lb, icy=350, lcy=395)
    with d.group("text_analytics"):
        d.icon("🔍", 274, 350, size=d.theme.size("icon")); d.text("Text\nAnalytics", 274, 392, size="body", color="ink")
    with d.group("raw"):
        d.icon("🗄️", 72, 456, size=d.theme.size("icon_sm")); d.text("Raw\nLanguage\nData", 72, 494, size="body", color="ink")
    d.rect(r2[1][0], 466, 80, 48, "**NLP**\n**System**", fill="tile_green", stroke="tile_green_line", rounded=6, size="body", color="ink", id="nlp_sys")
    with d.group("processed"):
        d.icon("📄", 282, 456, size=d.theme.size("icon_sm")); d.text("Processed\nInformation", 284, 498, size="body", color="ink")
    d.edge([(100, 490)], tgt="nlp_sys", color="ink", entry=(0, .5))
    d.edge([(220, 486), (240, 486), (240, 458), (264, 458)], src="nlp_sys", color="ink", exit=(1, .4))

    # --- NLU panel
    nlu = [("blue", "⚙️", "Semantic Role\nLabeling (SRL)", "srl"), ("purple", "🌳", "Named Entity\nRecognition", "ner"),
           ("purple", "🕸️", "Coreference\nResolution", "cor")]
    for box, (col, ic, lb, idn) in zip(d.fit_row(374, 651, 198, 3, 102, gap=9), nlu):   # same inner margin/gap/height in every panel
        tile(d, "t_" + idn, box, col, ic, lb, icy=230, lcy=274, size="label")
    with d.group("nlu_left"):
        d.rect(374, 308, 111, 222, fill="tile_blue", stroke="tile_blue_line", rounded=6)
        d.icon("🕸️", 398, 345, size=d.theme.size("icon_md")); d.text("Entity\n(NER)", 452, 342, size="body", color="ink")
        d.text("Coreference\nResolution", 428, 396, size="body", color="ink")
        d.icon("🧩", 428, 436, size=d.theme.size("icon_sm")); d.text("Word Sense\nDisambiguation\n(WSD)", 428, 478, size="label", color="ink")
    with d.group("nli"):
        d.rect(492, 308, 159, 222, fill="nli_fill", stroke="tile_purple_line", rounded=6)
        d.text("**NATURAL LANGUAGE**\n**INFERENCE (NLI)**", 572, 332, size="body", color="ink")
        d.text("Premise (P) & Hypothesis (H)", 572, 358, size="small", color="ink")
        d.text("Logical Relations:", 590, 397, size="small", color="ink")
        d.rect(500, 390, 25, 25, "P", fill="tile_blue", stroke="tile_blue_line", rounded=3, size="body", color="ink", id="P")
        d.rect(500, 437, 25, 25, "H", fill="hyp", stroke="tile_tan_line", rounded=3, size="body", color="ink", id="H")
        rel = d.column(538, 408, 3, 97, 22, gap=8)
        for (x, y, w, h), (lb, f, s, idn) in zip(rel, [("Entailment", "tile_green", "tile_green_line", "ent"),
                                                        ("Contradiction", "contra", "contra_line", "con"),
                                                        ("Neutral", "background", "neutral", "neu")]):
            d.rect(x, y, w, h, lb, fill=f, stroke=s, rounded=4, size="label", color="ink", id=idn)
        d.text("*(Examples for examples)*", 572, 506, size="small", color="muted")
    d.edge([], src="P", tgt="H", color="ink", sw="thin", exit=(.5, 1), entry=(.5, 0))
    for t in ("ent", "con", "neu"):  # branch: right out of H, then up/down into each relation
        d.edge([], src="H", tgt=t, color="ink", sw="thin", route="orthogonal", exit=(1, .5), entry=(0, .5))

    # --- NLG panel
    nlg = [("✍️", "Content\nDetermination", "cd"), ("🔀", "Sentence\nPlanning", "sp"), ("🌐", "Surface\nRealization", "sre")]
    boxes = d.fit_row(705, 982, 198, 3, 102, gap=9)
    for box, (ic, lb, idn) in zip(boxes, nlg):
        tile(d, "t_" + idn, box, "tan", ic, lb, icy=266, lcy=219, size="label")
    d.rect(810, 330, 95, 60, "**NLG**\n**Model**", fill="tile_tan", stroke="tile_tan_line", rounded=6, size="heading", color="ink", id="nlg_model")
    for (x, y, w, h), idn in zip(boxes, ("cd", "sp", "sre")):
        cx = x + w / 2
        tx = min(max(cx, 825), 890)
        d.edge([(cx, 300), (cx, 315), (tx, 315), (tx, 330)], src=f"t_{idn}_box", tgt="nlg_model", color="ink",
               exit=(.5, 1), entry=((tx - 810) / 95, 0))
    with d.group("data_intent"):
        d.icon("📄", 742, 354, size=d.theme.size("icon_sm")); d.text("Data/Intent", 742, 386, size="body", color="ink")
    d.edge([(768, 360)], tgt="nlg_model", color="ink", entry=(0, .5))
    d.edge([(927, 360)], src="nlg_model", color="ink", exit=(1, .5))
    with d.group("coherent"):
        d.icon("💬", 946, 352, size=d.theme.size("icon_sm")); d.text("Coherent\nText", 946, 394, size="body", color="ink")
    with d.group("applications"):
        for cy, s in zip((422, 446, 466, 487, 507), ("**APPLICATIONS:**", "•  Document Summarization",
                                                     "•  Dialogue Systems (Chatbots)", "•  Question Answering", "•  Paraphrasing")):
            d.text(s, 712, cy, anchor="w", size="body", color="ink")
    d.icon("💬", 946, 440, size=d.theme.size("icon_md")); d.icon("🔗", 958, 497, size=d.theme.size("icon_sm"))

    # footer rule with centered label
    d.line([(33, 547), (425, 547)], color="rule", sw="thin"); d.line([(600, 547), (990, 547)], color="rule", sw="thin")
    d.text("RESEARCH & EDUCATION", 512, 547, size="small", color="muted")


if __name__ == "__main__":
    run(layout, (1024, 559), THEME, "02_tile_dashboard")
