

import numpy as np
import pandas as pd
from typing import List


def precision_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    """
    Fraction of top-K recommendations that are relevant.
    Precision@K = |recommended[:k] ∩ relevant| / k
    """
    top_k = recommended[:k]
    hits = len(set(top_k) & set(relevant))
    return hits / k


def recall_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    """
    Fraction of relevant items found in top-K.
    In leave-one-out (one test item): = 1 if test item in top-K, else 0.
    """
    top_k = recommended[:k]
    hits = len(set(top_k) & set(relevant))
    return hits / len(relevant) if relevant else 0.0


def average_precision_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    """
    Average precision at each rank position where a relevant item is found.
    Rewards finding relevant items at earlier positions.
    MAP@K is the mean of this across all users.
    """
    relevant_set = set(relevant)
    hits = 0
    precision_sum = 0.0

    for i, item in enumerate(recommended[:k], start=1):
        if item in relevant_set:
            hits += 1
            precision_sum += hits / i

    return precision_sum / min(len(relevant), k) if relevant else 0.0


def ndcg_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    """
    Normalized Discounted Cumulative Gain.
    Rewards finding relevant items at top positions more than lower positions.

    DCG@K  = sum(1 / log2(i+1)) for relevant items at position i
    IDCG@K = best possible DCG (relevant items at positions 1..min(|rel|,k))
    NDCG@K = DCG@K / IDCG@K
    """
    relevant_set = set(relevant)
    dcg = 0.0

    for i, item in enumerate(recommended[:k], start=1):
        if item in relevant_set:
            dcg += 1.0 / np.log2(i + 1)

    # Ideal DCG: all relevant items at top positions
    idcg = sum(1.0 / np.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))

    return dcg / idcg if idcg > 0 else 0.0


def reciprocal_rank(recommended: List[str], relevant: List[str]) -> float:
    """
    1 / rank of first relevant item in the list.
    Returns 0 if no relevant item found.
    MRR is the mean of this across all users.
    """
    relevant_set = set(relevant)
    for i, item in enumerate(recommended, start=1):
        if item in relevant_set:
            return 1.0 / i
    return 0.0


def catalog_coverage(all_recommendations: List[List[str]], catalog_size: int) -> float:
    """
    Fraction of total catalog ever recommended across all users.
    Low coverage = popularity bias (same artists recommended to everyone).
    """
    recommended_items = set(item for recs in all_recommendations for item in recs)
    return len(recommended_items) / catalog_size


def intra_list_diversity(
    recommended: List[str],
    audio_lookup: dict
) -> float:
    """
    Average pairwise cosine DISTANCE between recommended artists.
    Higher = more diverse list.
    Only computed for artists with audio features.

    Distance = 1 - cosine_similarity
    """
    vecs = []
    for artist in recommended:
        vec = audio_lookup.get(artist)
        if vec is not None:
            vecs.append(np.array(vec, dtype=np.float32))

    if len(vecs) < 2:
        return 0.0

    distances = []
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            a, b = vecs[i], vecs[j]
            denom = np.linalg.norm(a) * np.linalg.norm(b)
            sim = float(np.dot(a, b) / denom) if denom > 1e-9 else 0.0
            distances.append(1.0 - sim)

    return float(np.mean(distances))


def novelty_score(recommended: List[str], pop_lookup: dict) -> float:
    """
    Average novelty of recommended items.
    Novelty of item i = 1 - popularity_score(i).
    Higher = recommending less well-known artists.
    """
    scores = [1.0 - pop_lookup.get(artist, 0.5) for artist in recommended]
    return float(np.mean(scores)) if scores else 0.0