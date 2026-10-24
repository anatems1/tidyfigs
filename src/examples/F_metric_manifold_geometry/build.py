"""Prototypes for passage F (Metric Geometry, Clustering Objectives, and Manifold Projections).
Run: python ../../scripts/prototype.py .
"""
import math
import os
import sys

from figlib import *
from drawio_kit import Diagram, measure_math


def v1(d):
    """v1: Continuous 2D Metric Space: Unit Hypersphere Arc, Cosine-Euclidean Equivalence, and K-means Centroid Attraction."""
    d.rect(20, 15, 1080, 390, fill="panel_bg", stroke="panel_border", sw="thin", rounded=8)
    d.text("Metric Geometry: Unit Normalization, Cosine Equivalence, and K-means Euclidean Space",
           35, 30, anchor="w", size="heading", bold=True, color="primary")
    d.text("Demonstrating monotonic relation ||u-v||_2^2 = 2 - 2(u·v) and WCSS / SSE centroid minimization (Equations 12 & 13)",
           35, 48, anchor="w", size="label", italic=True, color="neutral")

    # Left Sub-panel: Unit Normalization & Metric Equivalence
    d.rect(35, 70, 510, 320, fill="background", stroke="primary", sw="thin", rounded=6)
    d.text("**1. Unit Normalization & Cosine-Euclidean Equivalence**", 50, 90, anchor="w", size="label", bold=True, color="primary")

    ox, oy = 115, 235
    d.arrow([(ox, oy), (ox + 195, oy)], color="neutral", sw="thin")
    d.arrow([(ox, oy), (ox, oy - 150)], color="neutral", sw="thin")
    d.text("e_1", ox + 200, oy, anchor="w", size="small", color="neutral")
    d.text("e_2", ox, oy - 155, anchor="s", size="small", color="neutral")

    # Unit circle arc (r = 130)
    r = 130
    arc_pts = []
    for deg in range(0, 95, 10):
        rad = math.radians(deg)
        arc_pts.append((ox + int(r * math.cos(rad)), oy - int(r * math.sin(rad))))
    for i in range(len(arc_pts) - 1):
        d.line([arc_pts[i], arc_pts[i+1]], color="unit_circle", sw="thin")

    d.text("Unit circle ||u||_2 = 1", ox + 105, oy - 130, anchor="w", size="small", color="neutral")

    # Vectors u and v
    deg_u, deg_v = 65, 20
    ux = ox + int(r * math.cos(math.radians(deg_u)))
    uy = oy - int(r * math.sin(math.radians(deg_u)))
    vx = ox + int(r * math.cos(math.radians(deg_v)))
    vy = oy - int(r * math.sin(math.radians(deg_v)))

    d.arrow([(ox, oy), (ux, uy)], color="c1_color", sw="thick")
    d.circle(ux, uy, 4, fill="c1_color", stroke="c1_color")
    d.text("u (||u||_2 = 1)", ux - 6, uy - 10, anchor="e", size="small", bold=True, color="c1_color")

    d.arrow([(ox, oy), (vx, vy)], color="c3_color", sw="thick")
    d.circle(vx, vy, 4, fill="c3_color", stroke="c3_color")
    d.text("v (||v||_2 = 1)", vx + 8, vy + 4, anchor="w", size="small", bold=True, color="c3_color")

    # Angle theta and Chord
    d.text("θ", ox + 40, oy - 22, anchor="center", size="label", bold=True, color="primary")
    d.line([(ox + 30, oy - 5), (ox + 26, oy - 25)], color="primary", sw="thin")

    d.line([(ux, uy), (vx, vy)], color="split_line", sw="normal", dashed=True)
    d.text("||u - v||_2", (ux + vx) // 2 + 16, (uy + vy) // 2 - 6, anchor="center", size="small", bold=True, color="split_line")
    d.text("u · v = cos(θ)", ox + 45, oy + 16, anchor="w", size="small", color="primary")

    # Equivalence Card
    d.rect(50, 275, 480, 100, fill="panel_bg", stroke="primary", sw="thin", rounded=6)
    d.text("**Monotonic Equivalence Formulation:**\n\n"
           "**||u - v||_2² = 2 - 2(u · v) = 2 - 2 cos(θ)**\n\n"
           "• As angular proximity θ → 0, cosine similarity u · v → 1.\n"
           "• Minimizing Euclidean distance directly minimizes cosine distance on normalized embeddings.",
           65, 325, anchor="w", size="small", color="text")

    # Right Sub-panel: K-means in Euclidean Space
    d.rect(565, 70, 520, 320, fill="background", stroke="primary", sw="thin", rounded=6)
    d.text("**2. K-means Euclidean Space & Objective Function**", 580, 90, anchor="w", size="label", bold=True, color="primary")

    # Cluster 1 (C_1)
    c1_x, c1_y = 670, 165
    d.ellipse(c1_x - 65, c1_y - 50, 130, 100, fill="c1_light", fill_opacity="wash", stroke="c1_color", sw="hairline", dashed=True)
    d.text("Cluster C_1", c1_x - 20, c1_y - 38, anchor="center", size="small", bold=True, color="c1_color")
    d.rect(c1_x - 12, c1_y - 12, 24, 24, label="**μ_1**", fill="c1_color", stroke="primary", sw="normal", rounded=True, color="background", size="small")

    pts_c1 = [(c1_x - 40, c1_y - 25), (c1_x + 35, c1_y - 20), (c1_x - 25, c1_y + 30), (c1_x + 30, c1_y + 25)]
    for px, py in pts_c1:
        d.circle(px, py, 3, fill="c1_color", stroke="primary")
        d.line([(c1_x, c1_y), (px, py)], color="dist_line", sw="hairline", dashed=True)
    d.text("(x - μ_1)", c1_x - 24, c1_y - 10, anchor="center", size="small", italic=True, color="dist_line")

    # Cluster 2 (C_2)
    c2_x, c2_y = 940, 165
    d.ellipse(c2_x - 65, c2_y - 50, 130, 100, fill="c2_light", fill_opacity="wash", stroke="c2_color", sw="hairline", dashed=True)
    d.text("Cluster C_2", c2_x + 20, c2_y - 38, anchor="center", size="small", bold=True, color="c2_color")
    d.rect(c2_x - 12, c2_y - 12, 24, 24, label="**μ_2**", fill="c2_color", stroke="primary", sw="normal", rounded=True, color="background", size="small")

    pts_c2 = [(c2_x - 35, c2_y - 25), (c2_x + 40, c2_y - 18), (c2_x - 30, c2_y + 28), (c2_x + 30, c2_y + 30)]
    for px, py in pts_c2:
        d.circle(px, py, 3, fill="c2_color", stroke="primary")
        d.line([(c2_x, c2_y), (px, py)], color="dist_line", sw="hairline", dashed=True)
    d.text("(x - μ_2)", c2_x + 24, c2_y + 12, anchor="center", size="small", italic=True, color="dist_line")

    # WCSS Objective Card
    d.rect(580, 275, 490, 100, fill="panel_bg", stroke="primary", sw="thin", rounded=6)
    d.text("**K-means Minimization Objective (Eq. 12 & 13):**\n\n"
           "**WCSS = SSE = ∑_{i=1}^k ∑_{x ∈ C_i} (x - μ_i)²**\n\n"
           "• Evaluates each embedding **x** against cluster centroid **μ_i**.\n"
           "• Output partition: **C = {c_1, c_2, ..., c_k} = K-means[E(x), k]**.",
           595, 325, anchor="w", size="small", color="text")


def v2(d):
    """v2: Alternative Non-Euclidean Clustering: PDDP Divisive Hyperplane vs. HDBSCAN Density Cores & Noise."""
    d.rect(20, 15, 1080, 390, fill="panel_bg", stroke="panel_border", sw="thin", rounded=8)
    d.text("Non-Euclidean Clustering: PDDP Divisive Hyperplane vs. HDBSCAN Density Cores",
           35, 30, anchor="w", size="heading", bold=True, color="primary")
    d.text("Eigenvector SVD variance splitting (deterministic binary trees) vs. hierarchical density reachability with outlier noise segregation",
           35, 48, anchor="w", size="label", italic=True, color="neutral")

    # Left: PDDP
    d.rect(35, 70, 510, 320, fill="background", stroke="eigenvector", sw="thin", rounded=6)
    d.rect(35, 70, 510, 30, "**PDDP: Principal Direction Divisive Clustering** (Boley, 1998)", fill="eigenvector", stroke="eigenvector", color="background", rounded=6, size="label")

    pddp_ox, pddp_oy = 290, 190
    pts_pddp = [
        (-50, -20), (-35, -12), (-20, -5), (-10, -2), (0, 0),
        (15, 5), (30, 10), (48, 18), (-40, -5), (35, 5),
        (-25, -25), (25, 22), (-15, 10), (10, -10)
    ]
    for dx, dy in pts_pddp:
        d.circle(pddp_ox + dx, pddp_oy + dy, 3, fill="neutral", stroke="text")

    # Primary Eigenvector v_1
    d.arrow([(pddp_ox - 75, pddp_oy - 28), (pddp_ox + 75, pddp_oy + 28)], color="eigenvector", sw="thick")
    d.text("v_1 (Primary Eigenvector)", pddp_ox + 40, pddp_oy + 42, anchor="center", size="small", bold=True, color="eigenvector")

    # Splitting Hyperplane
    d.line([(pddp_ox - 22, pddp_oy + 55), (pddp_ox + 22, pddp_oy - 55)], color="split_line", sw="thick", dashed=True)
    d.text("SVD Splitting Hyperplane", pddp_ox + 35, pddp_oy - 50, anchor="w", size="small", bold=True, color="split_line")

    d.rect(50, 280, 480, 95, fill="panel_bg", stroke="panel_border", sw="thin", rounded=4)
    d.text("• **Mechanism:** Iteratively splits clusters along primary eigenvector of variance via SVD.\n"
           "• **Tree Structure:** Creates deterministic binary trees (Boley, 1998; Theocharopoulos et al., 2025).\n"
           "• **Geometry:** Divisive hyperplane partitioning rather than spherical Euclidean centroids.",
           65, 325, anchor="w", size="small", color="text")

    # Right: HDBSCAN
    d.rect(565, 70, 520, 320, fill="background", stroke="c3_color", sw="thin", rounded=6)
    d.rect(565, 70, 520, 30, "**HDBSCAN: Hierarchical Density-Based Clustering** (Campello et al., 2013)", fill="c3_color", stroke="c3_color", color="background", rounded=6, size="label")

    # Dense core 1
    hdb_cx, hdb_cy = 680, 185
    d.ellipse(hdb_cx - 50, hdb_cy - 40, 100, 80, fill="c3_light", fill_opacity="soft", stroke="c3_color", sw="thin")
    d.text("Dense Core 1", hdb_cx, hdb_cy, anchor="center", size="small", bold=True, color="c3_color")
    for dx, dy in [(-25, -10), (-10, 15), (15, -15), (20, 10), (0, -5), (-15, -20), (5, 20)]:
        d.circle(hdb_cx + dx, hdb_cy + dy, 3, fill="c3_color", stroke="primary")

    # Dense core 2
    hdb_c2x, hdb_c2y = 860, 175
    d.ellipse(hdb_c2x - 40, hdb_c2y - 30, 80, 60, fill="c1_light", fill_opacity="soft", stroke="c1_color", sw="thin")
    d.text("Dense Core 2", hdb_c2x, hdb_c2y, anchor="center", size="small", bold=True, color="c1_color")
    for dx, dy in [(-15, -5), (10, 8), (-5, 12), (12, -8)]:
        d.circle(hdb_c2x + dx, hdb_c2y + dy, 3, fill="c1_color", stroke="primary")

    # Outliers / Noise
    outliers = [(780, 155), (800, 215), (710, 240), (620, 235), (930, 210)]
    for ox, oy in outliers:
        d.rect(ox - 5, oy - 5, 10, 10, shape="diamond", fill="noise_color", stroke="primary", sw="thin")

    d.rect(940, 140, 130, 24, fill="noise_light", stroke="noise_color", sw="hairline", rounded=4)
    d.rect(950, 147, 10, 10, shape="diamond", fill="noise_color", stroke="primary", sw="thin")
    d.text("**Outlier Noise**", 1010, 152, anchor="center", size="small", bold=True, color="noise_color")

    d.rect(580, 280, 490, 95, fill="panel_bg", stroke="panel_border", sw="thin", rounded=4)
    d.text("• **Mechanism:** Operates on cluster density across varying scales.\n"
           "• **Noise Segregation:** Explicitly segregates outliers as unassigned noise (Campello et al., 2013).\n"
           "• **Advantage:** Discovers arbitrarily shaped clusters without enforcing spherical partitions.",
           595, 325, anchor="w", size="small", color="text")


def v3(d):
    """v3: Non-Linear Manifold Reduction: High-D Embedding Manifold vs. t-SNE vs. UMAP 2D Projections."""
    d.rect(20, 15, 1100, 390, fill="panel_bg", stroke="panel_border", sw="thin", rounded=8)
    d.text("Non-Linear Manifold Reduction for Clustering: High-D Space vs. t-SNE vs. UMAP",
           35, 30, anchor="w", size="heading", bold=True, color="primary")
    d.text("Comparing local neighborhood preservation against global Riemannian geometry and topological relationships",
           35, 48, anchor="w", size="label", italic=True, color="neutral")

    # Panel 1: High-D Space
    d.rect(35, 70, 260, 315, fill="background", stroke="primary", sw="thin", rounded=6)
    d.rect(35, 70, 260, 30, "**High-Dimensional Space**", fill="primary", stroke="primary", color="background", rounded=6, size="label")

    d.text("Embedding Matrix E(x) in R^(n × d)", 165, 115, anchor="center", size="small", color="neutral")
    d.circle(165, 185, 45, fill="panel_bg", stroke="primary", sw="thin", dashed=True)
    d.text("Complex Non-linear\nManifold (d >> 2)", 165, 185, anchor="center", size="small", align="center", color="primary")
    d.text("Normalized unit length ||u||_2 = 1", 165, 255, anchor="center", size="small", color="neutral")

    d.rect(45, 290, 240, 80, fill="panel_bg", stroke="panel_border", sw="thin", rounded=4)
    d.text("• Dimensionality curse hinders direct clustering.\n"
           "• Embeddings lie on complex non-linear submanifolds.",
           55, 330, anchor="w", size="small", color="text")

    # Projection Arrows
    d.arrow([(295, 160), (335, 130)], color="neutral", sw="thick")
    d.arrow([(295, 210), (335, 240)], color="secondary", sw="thick")
    d.text("t-SNE", 315, 135, anchor="center", size="small", bold=True, color="neutral")
    d.text("UMAP", 315, 235, anchor="center", size="small", bold=True, color="secondary")

    # Panel 2: t-SNE 2D Projection
    d.rect(345, 70, 370, 315, fill="background", stroke="neutral", sw="thin", rounded=6)
    d.rect(345, 70, 370, 30, "**t-SNE 2D Projection** (van der Maaten, 2008)", fill="neutral", stroke="neutral", color="background", rounded=6, size="label")

    d.text("Preserves local neighborhood probabilities in 2D", 530, 115, anchor="center", size="small", color="neutral")

    tsne_cx1, tsne_cy1 = 415, 175
    tsne_cx2, tsne_cy2 = 505, 215
    tsne_cx3, tsne_cy3 = 625, 165

    for cx, cy, col in [(tsne_cx1, tsne_cy1, "c1_color"), (tsne_cx2, tsne_cy2, "c2_color"), (tsne_cx3, tsne_cy3, "c3_color")]:
        d.circle(cx, cy, 18, fill=col, fill_opacity="wash", stroke=col, sw="hairline")
        for dx, dy in [(-8, -4), (6, -6), (-4, 7), (8, 5), (0, 0)]:
            d.circle(cx + dx, cy + dy, 3, fill=col, stroke=col)

    d.line([(tsne_cx1, tsne_cy1), (tsne_cx2, tsne_cy2)], color="split_line", sw="thin", dashed=True)
    d.line([(tsne_cx2, tsne_cy2), (tsne_cx3, tsne_cy3)], color="split_line", sw="thin", dashed=True)
    d.text("Distances distorted", 520, 180, anchor="center", size="small", color="split_line")

    d.rect(355, 290, 350, 80, fill="panel_bg", stroke="panel_border", sw="thin", rounded=4)
    d.text("• **Strength:** Exceptional for 2D visual cluster separation.\n"
           "• **Limitation:** Preserves neither global geometry nor distance scales.\n"
           "• **Scale:** Slow scaling to large document corpora.",
           365, 330, anchor="w", size="small", color="text")

    # Panel 3: UMAP 2D Projection
    d.rect(735, 70, 370, 315, fill="background", stroke="secondary", sw="thin", rounded=6)
    d.rect(735, 70, 370, 30, "**UMAP 2D Projection** (McInnes et al., 2018)", fill="secondary", stroke="secondary", color="background", rounded=6, size="label")

    d.text("Riemannian geometry & algebraic topology", 920, 115, anchor="center", size="small", color="neutral")

    umap_cx1, umap_cy1 = 805, 175
    umap_cx2, umap_cy2 = 890, 215
    umap_cx3, umap_cy3 = 1015, 165

    for cx, cy, col in [(umap_cx1, umap_cy1, "c1_color"), (umap_cx2, umap_cy2, "c2_color"), (umap_cx3, umap_cy3, "c3_color")]:
        d.circle(cx, cy, 18, fill=col, fill_opacity="wash", stroke=col, sw="hairline")
        for dx, dy in [(-8, -4), (6, -6), (-4, 7), (8, 5), (0, 0)]:
            d.circle(cx + dx, cy + dy, 3, fill=col, stroke=col)

    d.line([(umap_cx1, umap_cy1), (umap_cx2, umap_cy2)], color="c3_color", sw="normal")
    d.line([(umap_cx2, umap_cy2), (umap_cx3, umap_cy3)], color="c3_color", sw="normal")
    d.text("Global topology preserved", 910, 180, anchor="center", size="small", bold=True, color="c3_color")

    d.rect(745, 290, 350, 80, fill="panel_bg", stroke="panel_border", sw="thin", rounded=4)
    d.text("• **Strength:** Preserves both local clustering and global relationships.\n"
           "• **Theoretical Basis:** Grounded in Riemannian manifold geometry.\n"
           "• **Efficiency:** Scales efficiently to large document corpora.",
           755, 330, anchor="w", size="small", color="text")


INFERRED = [
    "v1: 2D coordinate frame and unit circle arc are visual geometric projections of high-dimensional unit hyperspheres",
    "v2: synthetic 2D point distributions and splitting hyperplanes illustrate SVD divisive variance and density cores",
    "v3: Swiss roll manifold and 3-cluster projections illustrate topological preservation vs distortion properties",
]

LINT_IGNORE = ["near-miss", "uneven gaps"]

ALLOWED_TERMS = [
    "unit", "circle", "chord", "cosine", "equivalence", "formulation", "proximity", "directly",
    "partition", "divisive", "hyperplane", "structure", "creates", "partitioning", "rather",
    "spherical", "reachability", "discovers", "arbitrarily", "shaped", "enforcing", "partitions",
    "strength", "limitation", "efficiency", "theoretical", "submanifolds", "curse", "hinders",
    "direct", "distorted", "separation", "slow", "scaling", "large", "basis", "grounded", "scales",
    "angular", "demonstrating", "equations", "output", "similarity", "advantage", "core", "cores",
    "dense", "mechanism", "splitting", "varying", "without", "comparing", "complex", "dimensional",
    "dimensionality", "document", "high", "lie", "matrix"
]

VARIANTS = [
    dict(key="v1", name="metric_geometry_clusters", size=(1120, 420), build=v1,
         about="Continuous 2D metric space: unit circle arc, cosine-Euclidean chord equivalence, and K-means centroid attraction.",
         caption="Metric space geometry: normalized transformer embeddings exhibit monotonic equivalence between Euclidean chord distance and cosine distance, while K-means minimizes centroid WCSS/SSE."),
    dict(key="v2", name="divisive_density_clustering", size=(1120, 420), build=v2,
         about="Alternative non-Euclidean clustering: PDDP SVD primary eigenvector splitting vs. HDBSCAN density cores and outlier noise.",
         caption="Non-Euclidean clustering methods: PDDP deterministically splits along principal eigenvectors of variance, whereas HDBSCAN clusters along density reachability and segregates outlier noise."),
    dict(key="v3", name="manifold_projection_spaces", size=(1140, 420), build=v3,
         about="Non-linear manifold reduction: High-D space compared to t-SNE and UMAP 2D projections.",
         caption="Manifold reduction for clustering: High-dimensional embeddings projected into 2D via t-SNE (local neighborhoods only) versus UMAP (preserving both local clustering and global Riemannian topology)."),
]
