"""Prototypes for passage E (Matrix Computation & Topic Models: NMF vs. LDA).
Run: python ../../scripts/prototype.py .
"""
import math
import os
import sys

from figlib import *
from drawio_kit import Diagram, measure_math


def v1(d):
    """v1: Explicit populated matrix factorization grid V ≈ W × H with cell dot-product arithmetic."""
    # Outer Panel
    d.rect(20, 15, 1080, 390, fill="panel_bg", stroke="panel_border", sw="thin", rounded=8)
    d.text("Non-negative Matrix Factorization (NMF): Linear Algebra Computation",
           35, 30, anchor="w", size="heading", bold=True, color="primary")
    d.text("Decomposing document-term frequency matrix V into topic word weights W and document topic weights H (V ≈ W × H)",
           35, 48, anchor="w", size="label", italic=True, color="neutral")

    # 1. Document-Term Matrix V (5 words × 5 docs)
    vx_top = 165
    d.text("**Document-Term Matrix V**", vx_top, 72, anchor="center", size="label", bold=True, color="v_matrix")
    d.text("Input frequency / TF-IDF matrix (5 × 5)", vx_top, 86, anchor="center", size="small", italic=True, color="neutral")

    doc_labels = ["d_1", "d_2", "d_3", "d_4", "d_5"]
    grid_vx, grid_vy = 105, 115
    cell_w, cell_h = 36, 26

    for j, d_lab in enumerate(doc_labels):
        d.text(d_lab, grid_vx + j * cell_w + cell_w // 2, grid_vy - 10, anchor="center", size="small", bold=True, color="text")

    word_labels = ["neural", "network", "factor", "topic", "corpus"]
    for i, w_lab in enumerate(word_labels):
        d.text(f"w_{i+1}: {w_lab}", grid_vx - 8, grid_vy + i * cell_h + cell_h // 2, anchor="e", size="small", color="text")

    v_data = [
        ["0.72", "0.00", "0.65", "0.00", "0.00"],
        ["0.55", "0.00", "0.58", "0.00", "0.00"],   # Target cell is (1, 2) -> network in d_3
        ["0.00", "0.45", "0.00", "0.62", "0.00"],
        ["0.00", "0.68", "0.15", "0.54", "0.40"],
        ["0.20", "0.35", "0.00", "0.30", "0.50"],
    ]

    target_r, target_c = 1, 2
    for r in range(5):
        for c in range(5):
            cx = grid_vx + c * cell_w
            cy = grid_vy + r * cell_h
            val = v_data[r][c]
            if r == target_r and c == target_c:
                d.rect(cx, cy, cell_w, cell_h, label=f"**{val}**", fill="calc_light", stroke="calc_highlight", sw="thick", size="small", color="calc_highlight")
            elif val == "0.00":
                d.rect(cx, cy, cell_w, cell_h, label=val, fill="sparse_zero", stroke="panel_border", sw="hairline", size="small", color="neutral")
            else:
                d.rect(cx, cy, cell_w, cell_h, label=val, fill="v_light", stroke="v_matrix", sw="thin", size="small", color="v_matrix")

    d.text("Sparse lexical frequencies", vx_top, 258, anchor="center", size="small", italic=True, color="v_matrix")

    # Approx Symbol
    d.text("≈", 305, 175, anchor="center", size="title", bold=True, color="primary")
    d.text("(Eq. 14)", 305, 198, anchor="center", size="small", bold=True, color="neutral")

    # 2. Topic Matrix W (5 words × 2 topics)
    wx_top = 405
    d.text("**Topic Matrix W**", wx_top, 72, anchor="center", size="label", bold=True, color="w_matrix")
    d.text("Word weights for each topic (K = 2)", wx_top, 86, anchor="center", size="small", italic=True, color="neutral")

    grid_wx, grid_wy = 355, 115
    w_col_w = 50
    d.text("t_1 (DL)", grid_wx + w_col_w // 2, grid_wy - 10, anchor="center", size="small", bold=True, color="w_matrix")
    d.text("t_2 (Mining)", grid_wx + w_col_w + w_col_w // 2, grid_wy - 10, anchor="center", size="small", bold=True, color="w_matrix")

    w_data = [
        ["0.82", "0.05"],
        ["0.75", "0.10"],   # Active Row 2 highlighted!
        ["0.04", "0.70"],
        ["0.08", "0.85"],
        ["0.15", "0.52"],
    ]

    for r in range(5):
        for c in range(2):
            cx = grid_wx + c * w_col_w
            cy = grid_wy + r * cell_h
            val = w_data[r][c]
            if r == target_r:
                d.rect(cx, cy, w_col_w, cell_h, label=f"**{val}**", fill="calc_light", stroke="calc_highlight", sw="normal", size="small", color="calc_highlight")
            else:
                d.rect(cx, cy, w_col_w, cell_h, label=val, fill="w_light", stroke="w_matrix", sw="thin", size="small", color="w_matrix")

    d.text("Word-topic distributions", wx_top, 258, anchor="center", size="small", italic=True, color="w_matrix")
    d.rect(grid_wx - 3, grid_wy + target_r * cell_h - 2, 2 * w_col_w + 6, cell_h + 4, fill="none", stroke="calc_highlight", sw="thick", rounded=4)
    d.text("Row w_2", grid_wx - 8, grid_wy + target_r * cell_h + cell_h // 2, anchor="e", size="small", bold=True, color="calc_highlight")

    # Multiply Symbol
    d.text("×", 485, 175, anchor="center", size="title", bold=True, color="primary")

    # 3. Coefficient Matrix H (2 topics × 5 docs)
    hx_top = 615
    d.text("**Coefficient Matrix H**", hx_top, 72, anchor="center", size="label", bold=True, color="h_matrix")
    d.text("Topic weights for each document", hx_top, 86, anchor="center", size="small", italic=True, color="neutral")

    grid_hx, grid_hy = 525, 145
    h_col_w = 36

    for j, d_lab in enumerate(doc_labels):
        d.text(d_lab, grid_hx + j * h_col_w + h_col_w // 2, grid_hy - 10, anchor="center", size="small", bold=True, color="text")

    d.text("t_1", grid_hx - 6, grid_hy + cell_h // 2, anchor="e", size="small", bold=True, color="h_matrix")
    d.text("t_2", grid_hx - 6, grid_hy + cell_h + cell_h // 2, anchor="e", size="small", bold=True, color="h_matrix")

    h_data = [
        ["0.88", "0.05", "0.70", "0.10", "0.05"],
        ["0.12", "0.85", "0.25", "0.80", "0.75"],
    ]

    for r in range(2):
        for c in range(5):
            cx = grid_hx + c * h_col_w
            cy = grid_hy + r * cell_h
            val = h_data[r][c]
            if c == target_c:
                d.rect(cx, cy, h_col_w, cell_h, label=f"**{val}**", fill="calc_light", stroke="calc_highlight", sw="normal", size="small", color="calc_highlight")
            else:
                d.rect(cx, cy, h_col_w, cell_h, label=val, fill="h_light", stroke="h_matrix", sw="thin", size="small", color="h_matrix")

    d.text("Document mixture weights", hx_top, 258, anchor="center", size="small", italic=True, color="h_matrix")
    d.rect(grid_hx + target_c * h_col_w - 2, grid_hy - 3, h_col_w + 4, 2 * cell_h + 6, fill="none", stroke="calc_highlight", sw="thick", rounded=4)
    d.text("Col d_3", grid_hx + target_c * h_col_w + h_col_w // 2, grid_hy + 2 * cell_h + 12, anchor="center", size="small", bold=True, color="calc_highlight")

    # 4. Calculation Trace Box (Right)
    d.rect(740, 68, 345, 215, fill="background", stroke="calc_highlight", sw="normal", rounded=6)
    d.text("**Actual Dot Product Arithmetic**", 755, 86, anchor="w", size="label", bold=True, color="calc_highlight")
    d.text(
        "**Reconstructing Cell V_{2,3} (word 'network' in doc d_3):**\n\n"
        "**V_{i,j} ≈ ∑_{r=1}^K (W_{i,r} × H_{r,j}) = w_{i,:} · h_{:,j}**\n\n"
        "**V_{2,3} ≈ (W_{2,1} × H_{1,3}) + (W_{2,2} × H_{2,3})**\n"
        "     **= (0.75 × 0.70) + (0.10 × 0.25)**\n"
        "     **= 0.525 + 0.025 = 0.55 ≈ 0.58**\n\n"
        "{neutral|• **Additive Non-negativity:** Both W ≥ 0 and H ≥ 0.}\n"
        "{neutral|• Parts-based representation without cancellation.}",
        755, 162, anchor="w", size="small"
    )
    d.arrow([(grid_wx + 2 * w_col_w + 4, grid_wy + target_r * cell_h + cell_h // 2), (735, 135)], color="calc_highlight", sw="thick")
    d.arrow([(grid_hx + target_c * h_col_w + h_col_w // 2, grid_hy - 6), (735, 155)], color="calc_highlight", sw="thick")
    d.rect(755, 244, 315, 26, label="**Reconstructs Target Cell V_{2,3} = 0.58**", fill="calc_light", stroke="calc_highlight", sw="normal", rounded=4, size="small", color="calc_highlight")

    # Bottom Summary Bar
    d.rect(35, 305, 1050, 68, fill="background", stroke="primary", sw="thin", rounded=6)
    d.text(
        "**Linear Algebra Insight:** High-dimensional sparse frequency matrix **V** (M × N) is factorized into topic matrix **W** (M × K word weights)\n"
        "and coefficient matrix **H** (K × N document weights), reducing dimensionality from M to K (K << M) while capturing thematic structure.",
        560, 339, anchor="center", size="small", align="center", color="primary"
    )


def v2(d):
    """v2: Comparative feature spaces: Raw TF-IDF Orthogonal Failure vs. NMF Low-Rank Space vs. LDA Generative Model."""
    d.rect(20, 15, 1100, 390, fill="panel_bg", stroke="panel_border", sw="thin", rounded=8)
    d.text("Graphical Comparison: Raw TF-IDF Space vs. NMF Low-Rank Space vs. LDA Generative Space",
           35, 30, anchor="w", size="heading", bold=True, color="primary")
    d.text("Demonstrating geometric representations, dimensionality compression, and generative assumptions",
           35, 48, anchor="w", size="label", italic=True, color="neutral")

    # Sub-panel 1: Raw TF-IDF Space
    d.rect(35, 70, 345, 315, fill="background", stroke="v_matrix", sw="thin", rounded=6)
    d.rect(35, 70, 345, 30, "**1. Raw TF-IDF Space** (Prior Concept)", fill="v_matrix", stroke="v_matrix", color="background", rounded=6, size="label")

    o1_x, o1_y = 135, 230
    d.arrow([(o1_x, o1_y), (o1_x + 130, o1_y)], color="neutral", sw="thin")
    d.arrow([(o1_x, o1_y), (o1_x, o1_y - 95)], color="neutral", sw="thin")
    d.arrow([(o1_x, o1_y), (o1_x - 45, o1_y + 35)], color="neutral", sw="thin")
    d.text("w_1 ('car')", o1_x + 135, o1_y, anchor="w", size="small", color="neutral")
    d.text("w_2 ('auto')", o1_x, o1_y - 100, anchor="s", size="small", color="neutral")
    d.text("w_3 ('neural')", o1_x - 50, o1_y + 35, anchor="e", size="small", color="neutral")

    d.arrow([(o1_x, o1_y), (o1_x + 90, o1_y)], color="v_matrix", sw="thick")
    d.circle(o1_x + 90, o1_y, 4, fill="v_matrix", stroke="v_matrix")
    d.text("Doc A ('car')", o1_x + 90, o1_y + 14, anchor="center", size="small", bold=True, color="v_matrix")

    d.arrow([(o1_x, o1_y), (o1_x, o1_y - 70)], color="secondary", sw="thick")
    d.circle(o1_x, o1_y - 70, 4, fill="secondary", stroke="secondary")
    d.text("Doc B ('auto')", o1_x + 6, o1_y - 75, anchor="w", size="small", bold=True, color="secondary")

    d.line([(o1_x + 18, o1_y), (o1_x + 18, o1_y - 18)], color="calc_highlight", sw="thin")
    d.line([(o1_x, o1_y - 18), (o1_x + 18, o1_y - 18)], color="calc_highlight", sw="thin")
    d.text("θ = 90° (cos θ = 0)", o1_x + 25, o1_y - 30, anchor="w", size="small", bold=True, color="calc_highlight")

    d.rect(45, 315, 320, 56, fill="sparse_zero", stroke="panel_border", sw="thin", rounded=4)
    d.text("• **Orthogonality Failure:** Synonyms have 0 similarity.\n"
           "• **Extreme Sparsity:** Dimensionality = |Vocabulary| (M ~ 10⁴).",
           55, 343, anchor="w", size="small", color="text")

    # Sub-panel 2: NMF Latent Semantic Subspace
    d.rect(395, 70, 345, 315, fill="background", stroke="w_matrix", sw="thin", rounded=6)
    d.rect(395, 70, 345, 30, "**2. NMF Latent Topic Space** (Linear Algebra)", fill="w_matrix", stroke="w_matrix", color="background", rounded=6, size="label")

    o2_x, o2_y = 470, 230
    d.arrow([(o2_x, o2_y), (o2_x + 145, o2_y)], color="w_matrix", sw="thin")
    d.arrow([(o2_x, o2_y), (o2_x, o2_y - 95)], color="h_matrix", sw="thin")
    d.text("t_1 (Automotive)", o2_x + 145, o2_y + 14, anchor="center", size="small", bold=True, color="w_matrix")
    d.text("t_2 (Mining)", o2_x, o2_y - 100, anchor="s", size="small", bold=True, color="h_matrix")

    d.rect(o2_x, o2_y - 95, 170, 95, fill="w_light", fill_opacity="wash", stroke="none")
    d.text("Non-negative Orthant (W, H ≥ 0)", o2_x + 75, o2_y - 80, anchor="center", size="small", italic=True, color="neutral")

    d.arrow([(o2_x, o2_y), (o2_x + 115, o2_y - 25)], color="v_matrix", sw="thick")
    d.arrow([(o2_x, o2_y), (o2_x + 105, o2_y - 36)], color="secondary", sw="thick")
    d.circle(o2_x + 115, o2_y - 25, 4, fill="v_matrix", stroke="v_matrix")
    d.circle(o2_x + 105, o2_y - 36, 4, fill="secondary", stroke="secondary")

    d.text("Doc A ('car')", o2_x + 120, o2_y - 20, anchor="w", size="small", bold=True, color="v_matrix")
    d.text("Doc B ('auto')", o2_x + 110, o2_y - 42, anchor="w", size="small", bold=True, color="secondary")
    d.text("θ ≈ 5° (cos θ ≈ 0.99)", o2_x + 40, o2_y - 30, anchor="center", size="small", bold=True, color="calc_highlight")

    d.rect(405, 315, 320, 56, fill="w_light", fill_opacity="soft", stroke="w_matrix", sw="hairline", rounded=4)
    d.text("• **Semantic Clustering:** Synonyms align along Topic 1.\n"
           "• **Low-Rank Compression:** Reduced to K topics (K << M).",
           415, 343, anchor="w", size="small", color="primary")

    # Sub-panel 3: LDA Generative Bayesian Model
    d.rect(755, 70, 345, 315, fill="background", stroke="h_matrix", sw="thin", rounded=6)
    d.rect(755, 70, 345, 30, "**3. LDA Generative Model** (Hierarchical Bayesian)", fill="h_matrix", stroke="h_matrix", color="background", rounded=6, size="label")

    pl_x, pl_y = 770, 115
    plate_cy = 180

    # Hyperparameter alpha
    d.circle(pl_x + 20, plate_cy, 14, fill="lda_light", stroke="lda_accent", sw="normal")
    d.text("α", pl_x + 20, plate_cy, anchor="center", size="label", bold=True, color="lda_accent")
    d.text("Dirichlet", pl_x + 20, 150, anchor="center", size="small", color="neutral")
    d.arrow([(pl_x + 34, plate_cy), (pl_x + 70, plate_cy)], color="primary", sw="thick")

    # Document Plate D
    d.rect(pl_x + 65, 125, 165, 115, fill="none", stroke="neutral", sw="thin", rounded=6)
    d.text("Document d in Corpus (D)", pl_x + 147, 230, anchor="center", size="small", italic=True, color="neutral")

    # theta_d (topic mixture for document d)
    d.circle(pl_x + 95, plate_cy, 14, fill="w_light", stroke="w_matrix", sw="normal")
    d.text("θ_d", pl_x + 95, plate_cy, anchor="center", size="label", bold=True, color="w_matrix")
    d.arrow([(pl_x + 109, plate_cy), (pl_x + 141, plate_cy)], color="primary", sw="thick")

    # Word Plate N
    d.rect(pl_x + 135, 135, 85, 80, fill="none", stroke="neutral", sw="hairline", rounded=4)
    d.text("Word n (N)", pl_x + 177, 205, anchor="center", size="small", color="neutral")

    # z_dn (topic indicator)
    d.circle(pl_x + 155, plate_cy, 12, fill="w_light", stroke="w_matrix", sw="normal")
    d.text("z", pl_x + 155, plate_cy, anchor="center", size="small", bold=True, color="w_matrix")
    d.arrow([(pl_x + 167, plate_cy), (pl_x + 188, plate_cy)], color="primary", sw="thick")

    # w_dn (observed word token)
    d.circle(pl_x + 200, plate_cy, 12, fill="calc_light", stroke="calc_highlight", sw="thick")
    d.text("w", pl_x + 200, plate_cy, anchor="center", size="small", bold=True, color="calc_highlight")

    # Topic Plate K and beta
    d.circle(pl_x + 285, plate_cy, 14, fill="lda_light", stroke="lda_accent", sw="normal")
    d.text("β", pl_x + 285, plate_cy, anchor="center", size="label", bold=True, color="lda_accent")
    d.text("Dirichlet", pl_x + 285, 150, anchor="center", size="small", color="neutral")
    d.arrow([(pl_x + 271, plate_cy), (pl_x + 215, plate_cy)], color="primary", sw="thick")

    d.rect(765, 315, 320, 56, fill="lda_light", fill_opacity="soft", stroke="lda_accent", sw="hairline", rounded=4)
    d.text("• **Generative Mechanism:** Documents are random topic mixtures.\n"
           "• **Probabilistic Foundations:** Discrete Dirichlet distributions.",
           775, 343, anchor="w", size="small", color="text")


def v3(d):
    """v3: Generative Probabilistic Architecture: Complete LDA Plate Model & Comparison with NMF Factorization."""
    d.rect(20, 15, 1080, 420, fill="panel_bg", stroke="panel_border", sw="thin", rounded=8)
    d.text("Latent Dirichlet Allocation (LDA) Generative Mechanism vs. NMF Factorization",
           35, 30, anchor="w", size="heading", bold=True, color="primary")
    d.text("Hierarchical Bayesian plate notation and paradigm contrast (Algebraic vs. Generative Probabilistic)",
           35, 48, anchor="w", size="label", italic=True, color="neutral")

    # Left: Deep Plate Diagram
    d.rect(35, 70, 540, 345, fill="background", stroke="primary", sw="thin", rounded=6)
    d.text("**LDA Hierarchical Bayesian Plate Notation**", 50, 90, anchor="w", size="label", bold=True, color="primary")

    # Priors alpha and beta
    d.circle(80, 195, 16, fill="lda_light", stroke="lda_accent", sw="normal")
    d.text("α", 80, 195, anchor="center", size="heading", bold=True, color="lda_accent")
    d.text("Dirichlet Prior\nover topics", 80, 150, anchor="center", size="small", color="neutral")

    d.arrow([(96, 195), (145, 195)], color="primary", sw="thick")

    # Plate D: Documents
    d.rect(140, 115, 275, 175, fill="none", stroke="primary", sw="thin", rounded=6)
    d.text("Documents d ∈ {1, ..., D}", 277, 280, anchor="center", size="small", bold=True, color="primary")

    # theta_d: topic distribution
    d.circle(180, 195, 16, fill="w_light", stroke="w_matrix", sw="normal")
    d.text("θ_d", 180, 195, anchor="center", size="label", bold=True, color="w_matrix")
    d.text("Topic mixture\nθ_d ~ Dir(α)", 180, 150, anchor="center", size="small", color="neutral")

    d.arrow([(196, 195), (240, 195)], color="primary", sw="thick")

    # Plate N: Words inside Doc d
    d.rect(235, 130, 165, 130, fill="none", stroke="neutral", sw="hairline", rounded=4)
    d.text("Words n ∈ {1, ..., N_d}", 317, 250, anchor="center", size="small", color="neutral")

    # z_dn: latent topic
    d.circle(270, 195, 14, fill="w_light", stroke="w_matrix", sw="normal")
    d.text("z_{dn}", 270, 195, anchor="center", size="small", bold=True, color="w_matrix")
    d.text("Latent topic", 270, 165, anchor="center", size="small", color="neutral")

    d.arrow([(284, 195), (326, 195)], color="primary", sw="thick")

    # w_dn: observed word
    d.circle(340, 195, 14, fill="calc_light", stroke="calc_highlight", sw="heavy")
    d.text("w_{dn}", 340, 195, anchor="center", size="small", bold=True, color="calc_highlight")
    d.text("Observed word", 340, 165, anchor="center", size="small", color="calc_highlight")

    # Topic Plate K and beta
    d.circle(525, 195, 16, fill="lda_light", stroke="lda_accent", sw="normal")
    d.text("β", 525, 195, anchor="center", size="heading", bold=True, color="lda_accent")
    d.text("Dirichlet Prior\nover vocab", 525, 150, anchor="center", size="small", color="neutral")

    d.arrow([(509, 195), (465, 195)], color="primary", sw="thick")

    d.rect(420, 115, 65, 175, fill="none", stroke="secondary", sw="thin", rounded=6)
    d.text("K topics", 452, 280, anchor="center", size="small", bold=True, color="secondary")

    d.circle(452, 195, 14, fill="h_light", stroke="h_matrix", sw="normal")
    d.text("ϕ_k", 452, 195, anchor="center", size="small", bold=True, color="h_matrix")
    d.text("Word dist\nϕ_k ~ Dir(β)", 452, 150, anchor="center", size="small", color="neutral")

    d.arrow([(438, 195), (354, 195)], color="primary", sw="thick")

    # Generative Step Checklist below plate
    d.rect(50, 305, 510, 95, fill="panel_bg", stroke="panel_border", sw="thin", rounded=4)
    d.text("**Generative Story:**\n"
           "1. For each topic k ∈ {1, ..., K}: draw word distribution ϕ_k ~ Dir(β)\n"
           "2. For each document d ∈ {1, ..., D}: draw topic mixture θ_d ~ Dir(α)\n"
           "3. For each word n ∈ {1, ..., N_d}: draw topic z_{dn} ~ Cat(θ_d), then word w_{dn} ~ Cat(ϕ_{z_{dn}})",
           60, 350, anchor="w", size="small", color="text")

    # Right: Paradigm Comparison Table
    d.rect(595, 70, 485, 345, fill="background", stroke="primary", sw="thin", rounded=6)
    d.text("**Comparison: Linear Algebra (NMF) vs. Generative Bayesian (LDA)**", 610, 90, anchor="w", size="label", bold=True, color="primary")

    headers = [("Property", 110), ("NMF (Lee & Seung, 1999)", 175), ("LDA (Blei et al., 2003)", 175)]
    ty, rh = 115, 48
    cx = 610
    for h, w in headers:
        d.rect(cx, ty, w, 28, f"**{h}**", fill="primary", stroke="background", color="background", size="small")
        cx += w

    rows = [
        ("Core Mechanism", "Matrix decomposition\nV ≈ W × H", "Hierarchical Bayesian model\nDirichlet-Multinomial mixtures"),
        ("Mathematical Basis", "Linear algebra\nNon-negative constraints (W, H ≥ 0)", "Probability theory\nLatent prior distributions (α, β)"),
        ("Representation", "Word weights W, doc weights H\nParts-based additive reconstruction", "Discrete word distributions ϕ_k\nRandom topic mixtures θ_d"),
        ("Predecessors", "Built upon BoW and TF-IDF\nSolves synonym orthogonality", "Built upon BoW and TF-IDF\nProbabilistic document mining"),
        ("Dimensionality", "Compresses M words to K topics\nDeterministic low-rank factor space", "Uncovers K latent topics\nFull posterior distribution"),
    ]

    for i, (prop, nmf_val, lda_val) in enumerate(rows):
        y = ty + 28 + i * rh
        bg = "secondary" if i % 2 == 0 else "background"
        op = "wash" if i % 2 == 0 else None
        d.rect(610, y, 110, rh, f"**{prop}**", fill=bg, fill_opacity=op, stroke="panel_border", sw="thin", size="small", color="primary")
        d.rect(720, y, 175, rh, nmf_val, fill=bg, fill_opacity=op, stroke="panel_border", sw="thin", size="small", color="text")
        d.rect(895, y, 175, rh, lda_val, fill=bg, fill_opacity=op, stroke="panel_border", sw="thin", size="small", color="text")


INFERRED = [
    "v1: numerical cell values for V, W, and H are concrete pedagogical instantiations",
    "v2: 3D orthogonal axes and 90° angle illustrate the geometric concept of BoW/TF-IDF term independence",
    "v2 & v3: Dirichlet hyperparameters α, β and latent indicators z, θ, ϕ reflect standard LDA formulation (Blei et al., 2003)",
]

LINT_IGNORE = ["near-miss", "uneven gaps"]

ALLOWED_TERMS = [
    "0.00", "0.025", "0.04", "0.05", "0.08", "0.10", "0.12", "0.15", "0.20", "0.25", "0.30", "0.35",
    "0.40", "0.45", "0.50", "0.52", "0.525", "0.54", "0.55", "0.58", "0.62", "0.65", "0.68", "0.70",
    "0.72", "0.75", "0.80", "0.82", "0.85", "0.88", "0.99", "actual", "arithmetic", "both", "capturing",
    "cell", "col", "computation", "dimensional", "dimensionality", "dot", "high", "lexical", "network",
    "product", "reducing", "representation", "row", "sparse", "while", "without", "align", "along",
    "assumptions", "auto", "automotive", "car", "clustering", "comparison", "compression", "cos",
    "demonstrating", "foundations", "geometric", "graphical", "have", "low", "mechanism", "rank",
    "raw", "reduced", "representations", "semantic", "similarity", "space", "basis", "built", "cat",
    "constraints", "contrast", "core", "deterministic", "draw", "mathematical", "multinomial",
    "notation", "observed", "reconstruction", "theory", "additive", "based", "cancellation", "insight",
    "parts", "reconstructing", "reconstructs", "target", "extreme", "failure", "orthant", "orthogonality",
    "sparsity", "synonyms", "compresses", "full", "paradigm", "plate", "posterior", "predecessors",
    "property", "solves", "story", "synonym"
]

VARIANTS = [
    dict(key="v1", name="matrix_factorization_grid", size=(1120, 420), build=v1,
         about="Populated 2D matrix grids for V ≈ W × H with active row × column dot product reconstruction.",
         caption="Non-negative Matrix Factorization: decomposing document-term matrix V into word topic weights W and document topic weights H."),
    dict(key="v2", name="comparative_feature_spaces", size=(1140, 420), build=v2,
         about="Three comparative feature spaces: Raw TF-IDF orthogonal failure vs. NMF low-rank subspace vs. LDA generative model.",
         caption="Comparison of document representations: TF-IDF orthogonal word axes fail on synonyms, whereas NMF projects documents onto shared semantic topic rays and LDA models topic mixtures."),
    dict(key="v3", name="hierarchical_generative_plate", size=(1120, 450), build=v3,
         about="Hierarchical Bayesian plate notation for LDA with hyperparameters and generative story, contrasted with NMF.",
         caption="Latent Dirichlet Allocation: generative probabilistic plate model with Dirichlet priors and discrete word distributions, contrasted with algebraic NMF."),
]
