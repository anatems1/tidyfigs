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
