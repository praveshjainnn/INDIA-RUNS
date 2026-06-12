"""Embedder — local sentence-transformers embeddings + cosine similarity.
Uses all-MiniLM-L6-v2: fast, lightweight, runs on CPU, zero cost.
"""
from __future__ import annotations
import os

# Must be set BEFORE any tensorflow/protobuf import
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
import numpy as np
from typing import List, Optional
from ..config import EMBEDDING_MODEL


_model = None  # Lazy-loaded singleton


def get_model():
    """Lazy-load the sentence-transformer model once."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_text(text: str) -> np.ndarray:
    """Embed a single text string → numpy vector."""
    model = get_model()
    return model.encode(text, convert_to_numpy=True, normalize_embeddings=True)


def embed_batch(texts: List[str], batch_size: int = 64, show_progress: bool = False) -> np.ndarray:
    """
    Embed a list of texts → 2D numpy array [N x dim].
    Returns normalized (unit-length) vectors so cosine similarity = dot product.
    """
    model = get_model()
    return model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=show_progress,
    )


def cosine_similarity_single(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Cosine similarity between two unit vectors (= dot product since normalized)."""
    return float(np.dot(vec_a, vec_b))


def cosine_similarity_matrix(query_vec: np.ndarray, doc_matrix: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarities between a query vector and a matrix of document vectors.
    Returns a 1D array of scores [N].
    Both inputs must be L2-normalized (which embed_text/embed_batch guarantee).
    """
    return doc_matrix @ query_vec  # dot product since vectors are normalized


def rank_by_embedding(
    jd_text: str,
    candidate_narratives: List[str],
    candidate_ids: List[str],
    top_n: Optional[int] = None,
) -> List[tuple[str, float]]:
    """
    Embed JD and all candidates, return sorted [(candidate_id, cosine_score)] descending.
    """
    jd_vec = embed_text(jd_text)
    candidate_vecs = embed_batch(candidate_narratives, show_progress=True)
    scores = cosine_similarity_matrix(jd_vec, candidate_vecs)

    results = sorted(
        zip(candidate_ids, scores.tolist()),
        key=lambda x: -x[1]
    )
    if top_n:
        results = results[:top_n]
    return results
