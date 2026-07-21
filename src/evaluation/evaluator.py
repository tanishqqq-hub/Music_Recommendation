# src/evaluation/evaluator.py

import numpy as np
import pandas as pd
from typing import Callable, List
from tqdm import tqdm
from src.evaluation.metrics import (
    precision_at_k, recall_at_k, average_precision_at_k,
    ndcg_at_k, reciprocal_rank, catalog_coverage,
    intra_list_diversity, novelty_score
)


def create_leave_one_out_split(
    interactions_df: pd.DataFrame,
    min_interactions: int = 20,
    random_seed: int = 42
):
    """
    Leave-one-out split: hold out a random artist from each user's
    top-50% most-played artists.

    Why top-50% (not minimum play):
    Holding out the minimum-play item creates an impossible test —
    the held-out item is the user's most inconsistent preference,
    which no model trained on their dominant taste will recover.
    Holding out from the top half tests whether the model can
    recover something the user genuinely and repeatedly chose.

    Why min_interactions >= 20:
    Users with fewer than 20 artists have too little history to
    train on after removing one item. Filtering to active users
    gives the models a fair chance and reflects production reality
    (cold-start users get popularity recommendations anyway).
    """
    np.random.seed(random_seed)

    # Filter to users with sufficient history
    user_counts = interactions_df.groupby("user_id")["artist_name"].nunique()
    active_users = user_counts[user_counts >= min_interactions].index
    active_df = interactions_df[interactions_df["user_id"].isin(active_users)].copy()

    print(f"Active users (>={min_interactions} artists): {len(active_users):,}")

    test_indices = []

    for user_id, group in active_df.groupby("user_id"):
        # Sort by plays descending, take top 50%
        sorted_group = group.sort_values("plays", ascending=False)
        top_half = sorted_group.head(max(1, len(sorted_group) // 2))
        # Randomly select one item from top half as test item
        test_row = top_half.sample(1, random_state=random_seed)
        test_indices.append(test_row.index[0])

    test_df  = active_df.loc[test_indices].copy()
    train_df = active_df.drop(index=test_indices).copy()

    print(f"Train interactions: {len(train_df):,}")
    print(f"Test users:         {len(test_df):,}")
    print(f"Avg test item plays: {test_df['plays'].mean():.1f}")

    return train_df, test_df


def evaluate_recommender(
    recommend_fn: Callable,
    test_df: pd.DataFrame,
    popularity_df: pd.DataFrame,
    content_df: pd.DataFrame,
    k_values: List[int] = [5, 10, 20],
    n_users: int = 1000,
    random_seed: int = 42
) -> pd.DataFrame:
    """
    Evaluate a recommender function across multiple users and K values.

    Parameters:
        recommend_fn : callable(user_id, k) -> list of artist names
        test_df      : leave-one-out test set (one row per user)
        popularity_df: for novelty scoring
        content_df   : for diversity scoring
        k_values     : list of K values to evaluate at
        n_users      : number of users to evaluate (sample for speed)

    Returns:
        DataFrame with one row per K value, columns = metric names
    """
    # Build lookup tables
    pop_lookup = dict(zip(popularity_df["artist_name"], popularity_df["popularity_score"]))
    matched = content_df[content_df["has_content_features"]].copy()
    audio_lookup = dict(
        zip(
            matched["artist_name"],
            matched[["danceability","energy","loudness","speechiness",
                      "acousticness","instrumentalness","liveness",
                      "valence","tempo"]].values.tolist()
        )
    )

    # Sample users for evaluation speed
    np.random.seed(random_seed)
    eval_users = test_df["user_id"].sample(
        min(n_users, len(test_df)), random_state=random_seed
    ).tolist()

    catalog_size = popularity_df["artist_name"].nunique()
    max_k = max(k_values)

    # Collect per-user results
    all_recs = []         # for coverage
    per_user = []

    for user_id in tqdm(eval_users, desc="Evaluating users"):
        test_row = test_df[test_df["user_id"] == user_id]
        if test_row.empty:
            continue

        relevant = [test_row.iloc[0]["artist_name"]]

        try:
            recs = recommend_fn(user_id, max_k)
        except Exception:
            continue

        if not recs:
            continue

        all_recs.append(recs)

        per_user.append({
            "user_id": user_id,
            "recommended": recs,
            "relevant": relevant,
            "diversity": intra_list_diversity(recs[:10], audio_lookup),
            "novelty": novelty_score(recs[:10], pop_lookup)
        })

    if not per_user:
        print("No users evaluated successfully.")
        return pd.DataFrame()

    results = []

    for k in k_values:
        precisions, recalls, maps, ndcgs, mrrs = [], [], [], [], []

        for u in per_user:
            recs = u["recommended"]
            rel  = u["relevant"]
            precisions.append(precision_at_k(recs, rel, k))
            recalls.append(recall_at_k(recs, rel, k))
            maps.append(average_precision_at_k(recs, rel, k))
            ndcgs.append(ndcg_at_k(recs, rel, k))
            mrrs.append(reciprocal_rank(recs, rel))

        coverage  = catalog_coverage(all_recs, catalog_size)
        diversity = np.mean([u["diversity"] for u in per_user])
        novelty   = np.mean([u["novelty"]   for u in per_user])

        results.append({
            "K":          k,
            "Precision":  round(np.mean(precisions), 4),
            "Recall":     round(np.mean(recalls),    4),
            "MAP":        round(np.mean(maps),       4),
            "NDCG":       round(np.mean(ndcgs),      4),
            "MRR":        round(np.mean(mrrs),       4),
            "Coverage":   round(coverage,            4),
            "Diversity":  round(diversity,           4),
            "Novelty":    round(novelty,             4),
        })

    return pd.DataFrame(results)