#!/usr/bin/env python3
"""
Tier 4 — complex scientific figure (manifold hypothesis, 3-D surface + 2-D projection), 1408x768.
Shows: pseudo-3-D mesh surface (surface_mesh -> embedded SVG), wireframe cube with back/front edge
z-ordering, seeded scatter points (inside a polygon with keep-out zones, and along a curve),
photos cropped from the source (image_crop), translucent projection beams (polygon), stars,
closed curved loop, dashed straight-line distance attached to two stars, callouts with pointers,
small-caps serif title (raw HTML), justified serif caption with italics, credit line.
Run with --image pointing at the source so the two photo crops can be extracted.
"""
import math

from _common import run

THEME = {
    "colors": {"chunk_b": "#5b8c4a", "cluster_d": "#c2a27a"},
    "sizes": {"title": 30, "heading": 24, "body": 18.5, "label": 17, "subheading": 20, "small": 12.5, "caption": 23.5},
    "opacity": {"tint": 18, "beam": 28, "soft": 35, "chunk_c": 75, "faded": 35},
}


def photo(d, bbox, label):
    if d.source:
        return d.image_crop(bbox, border="text")
    x0, y0, x1, y1 = bbox
    return d.rect(x0, y0, x1 - x0, y1 - y0, f"*[photo: {label}]*", fill="neutral", fill_opacity="soft", size="small")


def layout(d):
    d.text('<span style="font-variant: small-caps">Visualizing the Manifold Hypothesis: Chunk A vs. Chunk B Geometry</span>',
           704, 30, w=1200, size="title", font="serif", raw=True)

    # ================= Panel A =================
    d.rect(35, 57, 665, 538, rounded=12, sw="thick", id="panelA")
    d.text("**A) Ambient High-Dimensional Data Space (D=3,072)**", 50, 85, anchor="w", size="heading")
    for p in ([(330, 110), (330, 410)], [(330, 410), (152, 465)], [(330, 410), (678, 505)]):   # back edges
        d.line(p, color="neutral", sw="thin")
    cube = [(152, 165), (330, 110), (678, 165), (678, 505), (340, 590), (152, 465)]
    keepout = [(40, 120, 218, 192), (470, 105, 660, 182), (572, 203, 684, 352), (500, 368, 692, 432),
               (448, 470, 696, 582), (40, 518, 305, 578), (40, 330, 158, 448), (44, 194, 150, 314)]
    pts = d.scatter_in_polygon(cube, 190, keepout=keepout, min_dist=12, seed=7)
    with d.group("points_behind"):
        for x, y in pts[::2]:
            d.dot(x, y, 4.5, fill="neutral", stroke="text", stroke_opacity=25)
    d.surface_mesh(back=[(172, 345), (240, 240), (330, 185), (430, 200), (510, 255), (548, 320)],
                   front=[(176, 352), (240, 420), (325, 495), (410, 470), (490, 385), (550, 326)],
                   nu=30, nv=14, bulge=38, fill="secondary", fill_opacity="tint", line="primary", id="manifold_surface")
    d.polygon([(143, 203), (143, 307), (282, 286), (280, 276)], fill="secondary", fill_opacity="beam", id="beam_A")
    d.polygon([(581, 215), (581, 343), (500, 309), (500, 301)], fill="chunk_b", fill_opacity="beam", id="beam_B")
    photo(d, (49, 199, 143, 309), "sound concrete")
    photo(d, (581, 211, 676, 346), "alligator cracking")
    loop = [(300, 272), (318, 250), (380, 252), (455, 288), (470, 312), (400, 330), (372, 356), (330, 322), (312, 290), (300, 272)]
    d.line(loop, color="primary", sw=3, route="curved", id="manifold_loop")
    d.star(289, 281, 34, fill="secondary", id="star_A")
    d.star(491, 305, 34, fill="chunk_b", id="star_B")
    d.edge([], src="star_A", tgt="star_B", arrow=None, dashed=True, sw="normal", id="geometric_distance")
    with d.group("points_front"):
        for x, y in pts[1::2]:
            d.dot(x, y, 4.5, fill="neutral", stroke="text", stroke_opacity=25)
    for p in ([(152, 165), (152, 465)], [(152, 165), (330, 110)], [(330, 110), (678, 165)], [(678, 165), (678, 505)],
              [(152, 465), (340, 590)], [(340, 590), (678, 505)]):                                   # front edges
        d.line(p, sw="normal")
    d.text("{secondary|**CHUNK A:**} Sound\nConcrete Pavement\n(3,072-D Vector)", 128, 160)
    d.text("**Latent Manifold** of\nMeaningful Human\nLanguage", 565, 145)
    d.text("{chunk_b|**CHUNK B:**}\nAlligator\nCracking\nDistress\n(3,072-\nD Vector)", 96, 388)
    d.text("**Geometric Distance**\n(Cosine Similarity,\nstraight line - Mismatch)", 592, 402, size="label")
    d.text("**True Semantic**\n**Distance** along Manifold", 170, 548)
    arr = dict(route="curved", sw="normal", head_size=7)
    d.arrow([(205, 150), (275, 160), (281, 265)], **arr)          # middle point = curve CONTROL point
    d.arrow([(458, 162), (412, 170), (408, 215)], **arr)
    d.arrow([(152, 338), (210, 288), (272, 286)], **arr)
    d.arrow([(512, 380), (465, 345), (410, 343)], dashed=True, **arr)
    d.arrow([(180, 502), (182, 462), (240, 462)], **arr)
    d.arrow([(282, 522), (312, 515), (312, 478)], **arr)
    d.callout(455, 475, 235, 100, "**Topological Mismatch:**\nLinear distance metrics often\ncut through empty space\nbetween manifold folds.",
              tip=(444, 402), base_at=497, fill="neutral", fill_opacity="soft", size="label", id="callout_topo")

    # ================= Panel B =================
    d.rect(712, 57, 681, 538, rounded=12, sw="thick", id="panelB")
    d.text("**B) Unfolded Latent Manifold Projection (d=2)**", 727, 85, anchor="w", size="heading")

    def arc_y(x):
        return 270 + (0.0020 if x < 1042 else 0.00247) * (x - 1042) ** 2
    # curved edge: waypoints are control points, so sample densely to pin the curve to the parabola
    d.line([(742, 465)] + [(x, arc_y(x)) for x in range(770, 1340, 30)] + [(1344, 465)], color="secondary", sw=3.5, route="curved")
    with d.group("points_2d"):
        for i, (x, y) in enumerate(d.scatter_along(arc_y, 750, 905, 38, spread=26, min_dist=10.5, seed=1)):
            d.dot(x, y, 5.5, fill="neutral", stroke="text", stroke_opacity=25)
        for i, (x, y) in enumerate(d.scatter_along(arc_y, 905, 950, 6, spread=22, min_dist=10.5, seed=2)):
            d.dot(x, y, 5.5, fill="neutral", stroke="text", stroke_opacity=25, opacity="faded" if i == 5 else None)
        for x, y in d.scatter_along(arc_y, 1040, 1105, 7, spread=14, min_dist=10.5, seed=3):
            d.dot(x, y, 5.5, fill="neutral", stroke="text", stroke_opacity=25)
        for x, y in d.scatter_along(arc_y, 1165, 1312, 34, spread=18, min_dist=10.5, seed=4):
            d.dot(x, y, 5.5, fill="cluster_d", stroke="text", stroke_opacity=25)
    d.star(877, 325, 34, fill="secondary", id="star_A_2d")
    d.star(1067, 276, 34, fill="secondary", opacity="chunk_c", id="star_C_2d")
    d.star(1227, 343, 34, fill="chunk_b", id="star_B_2d")
    d.text("Clustering of related pavement\nengineering concepts", 1032, 157)
    d.arrow([(947, 190), (895, 195), (890, 250)], **arr)
    d.arrow([(1117, 180), (1175, 185), (1178, 228)], **arr)
    d.text("{secondary|**Chunk A:**}", 870, 284, size="subheading")
    d.text("**Chunk C:**\nMinor Joint Spalling", 1068, 236)
    d.text("**Chunk D:**\nModerate\nSurface Scaling", 1262, 242)
    d.text("{chunk_b|**Chunk B:**}\nAlligator Cracking", 1068, 344, size="subheading")
    d.arrow([(842, 402), (1010, 495), (1212, 380)], **arr)
    d.arrow([(848, 412), (1040, 560), (1266, 408)], **arr)
    d.text("**Semantic Continuity**\npreserved by\nManifold Hypothesis", 1043, 520)
    d.callout(1162, 475, 186, 82, "**RAG target:** Retrieve\ncontext based on local\nmanifold proximity.",
              tip=(1228, 384), base_at=1232, size="label", id="callout_rag")

    # ================= credit + caption =================
    d.text("Figure adapted from Mason Smetana\u2019s Doctoral Dissertation (University of Pittsburgh, "
           "Swanson School of Engineering, 2026).", 1393, 607, anchor="e", size="small")
    d.text("Figure 1: Geometric representation of the Manifold Hypothesis applied to two engineering text chunks. "
           "(A) Shows Chunk A and Chunk B in high-dimensional ambient space. While computationally close in D-space, "
           "straight-line distance misinterprets the manifold curvature. (B) Illustrates the same points on an unfolded "
           "2D semantic manifold, where true conceptual *proximity* and *continuity* are revealed, critical for "
           "optimizing semantic retrieval in RAG systems.",
           35, 692, w=1360, h=130, anchor="w", size="caption", font="serif", wrap=True, extra={"align": "left"})


if __name__ == "__main__":
    run(layout, (1408, 768), THEME, "04_complex_manifold")
