# Passage: Non-negative Matrix Factorization and Latent Dirichlet Allocation

For two decades, the standard unsupervised techniques for literature and document mining were Non-negative Matrix Factorization (NMF) (Lee & Seung, 1999) and Latent Dirichlet Allocation (LDA) (Blei et al., 2003). NMF is a linear algebra technique that decomposes a document-term matrix (the input document-term frequency matrix, V) into two smaller non-negative matrices: 

$$V \approx W \times H \quad (14)$$

where W is the topic matrix, containing the word weights for each topic, and H is the coefficient matrix, containing the topic weights for each document. LDA on the other hand is a generative probabilistic hierarchical Bayesian model. It posits that each document d in a corpus is a random mixture over K latent topics, and each topic k is a discrete distribution over vocabulary words.  
Such approaches build upon the prior concepts of BoW and TF-IDF, providing powerful tools for uncovering latent thematic structure in large, unlabeled text corpora. Since they were modeled long before the advent of more advanced neural processes.
