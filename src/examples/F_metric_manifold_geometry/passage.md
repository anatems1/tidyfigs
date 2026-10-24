# Passage: Metric Distance, Clustering Objectives, and Manifold Projection

When transformer embeddings are normalized to unit length (|u|_2=1) squared Euclidean distance is monotonically related to cosine distance: |u-v|_2^2=2-2(u⋅v). K-means in particular operates in the Euclidean space, with an objective functions of minimizing within-cluster sum of squares (WCSS), also known as sum of square error (SSE):

$$\text{WCSS} = \text{SSE} = \sum_{i=1}^k \sum_{x \in C_i} (x - \mu_i)^2 \quad (12)$$

where x is each embedding evaluated against the centroid embedding μ for each cluster C_i it belongs to, such that:

$$C = \{c_1, c_2, \dots, c_k\} = \text{K-means}[E(x), k] \quad (13)$$

Other clustering methods are not inherently Euclidean-based, including principal direction divisive clustering (PDDP) and hierarchal density-based spatial clustering of applications with noise (HDBSCAN). PDDP iteratively splits clusters along their primary eigenvector of variance via singular value decomposition, creating deterministic binary trees (Boley, 1998; Theocharopoulos et al., 2025). Conversely, HDBSCAN operates on cluster density, explicitly segregating outliers as unassigned noise (Campello et al., 2013).
Effective clustering frequently benefits from non-linear manifold reduction, which can be achieved through t-distributed Stochastic Neighborhood Embeddings (t-SNE) or Uniform Manifold Approximation and Projection (UMAP). t-SNE preserves local neighborhood probabilities, exceptional for 2D visualization but preserves neither global geometry nor distance scales (van der Maaten & Hinton, 2008). UMAP is grounded in Riemannian geometry and algebraic topology, preserves both local clustering and global inter-cluster relationships while scaling efficiently to large corpora (McInnes et al., 2018).
