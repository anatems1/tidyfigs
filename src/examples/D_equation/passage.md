# Equation — hybrid relevance score

Each candidate chunk $d$ is scored against the query $q$ with a hybrid relevance function
$$s(q,d) = \lambda\,\mathrm{sim}(\mathbf{q},\mathbf{d}) + (1-\lambda)\,\mathrm{BM25}(q,d),$$
where $\mathrm{sim}(\mathbf{q},\mathbf{d}) = \frac{\mathbf{q}\cdot\mathbf{d}}{\lVert\mathbf{q}\rVert\,\lVert\mathbf{d}\rVert}$
is the cosine similarity between the 3,072-dimensional embeddings of the query and the chunk,
$\mathrm{BM25}(q,d)$ is a lexical matching score normalized to $[0,1]$, and $\lambda \in [0,1]$ controls
the balance between semantic and lexical evidence. Setting $\lambda = 1$ recovers pure dense retrieval,
whereas $\lambda = 0$ reduces to keyword search; in our experiments $\lambda = 0.7$ gave the best answer
accuracy. The top-$k$ chunks ranked by $s(q,d)$ are passed to the re-ranker.
