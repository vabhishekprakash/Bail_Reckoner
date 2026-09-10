"""Layer A — statutory corpus ingestion and retrieval.

Hierarchy-aware chunking over bare acts and special statutes, hybrid BM25 + dense retrieval,
cross-encoder reranking, and statute versioning. Measured by Recall@k and MRR against queries
with known statutory targets (M4).

Retrieval augmentation is measured, never assumed to help: the published IBPS result (arXiv
2508.07592) records naive RAG reducing that system's baseline accuracy from 0.47 to 0.33. If the
reranker has to be dropped for time, hybrid retrieval stays (CLAUDE.md section 5).

Nothing in this package participates in the decision path.
"""
