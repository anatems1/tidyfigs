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
