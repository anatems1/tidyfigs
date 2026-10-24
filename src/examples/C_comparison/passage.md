# Comparison — methods for distress identification

Three families of methods have been applied to automated pavement distress identification from textual
inspection records. Rule-based systems rely on keyword dictionaries and expert-defined heuristics; they
require no training data and are fully interpretable, but they generalize poorly to unseen terminology
and are costly to maintain. Classical machine-learning models, such as support vector machines trained
on TF-IDF features, require moderate amounts of labeled data, offer partial interpretability through
feature weights, and generalize reasonably within a single agency's vocabulary. Large language model
(LLM) approaches, used either through prompting or fine-tuning, need little task-specific labeled data
and generalize best across agencies and writing styles, but they are the least interpretable and carry
the highest computational cost. These trade-offs suggest that no single approach dominates; the
appropriate choice depends on data availability, the need for auditability, and deployment budget.
