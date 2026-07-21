# src/recommenders/collaborative.py

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix


class CollaborativeFilteringRecommender:

    def __init__(self, n_neighbors: int = 50):
        self.n_neighbors = n_neighbors
        self.matrix = None
        self.user_enc = None
        self.artist_enc = None
        self.idx_to_artist = None        # precomputed reverse mapping: int -> artist name
        self.interactions_df = None
        self.matrix_T_filtered = None
        self.active_artist_indices = None
        self.is_fitted = False

    def fit(self, matrix: csr_matrix, user_enc, artist_enc, interactions_df: pd.DataFrame):
        self.matrix = matrix
        self.user_enc = user_enc
        self.artist_enc = artist_enc
        self.interactions_df = interactions_df.copy()

        # Precompute reverse mapping — replaces inverse_transform() calls in hot loops
        # artist_enc.classes_ is a numpy array where classes_[i] = artist name for index i
        # This turns each lookup from ~29ms (sklearn overhead) to nanoseconds (array index)
        self.idx_to_artist = self.artist_enc.classes_.tolist()

        # Precompute filtered artist matrix for item-based CF
        # Keep only artists appearing in >= 5 user histories
        # Reduces 145K artist space to ~20-30K, cuts item-CF computation significantly
        artist_counts = np.asarray(self.matrix.sum(axis=0)).flatten()
        self.active_artist_mask = artist_counts >= 5
        self.active_artist_indices = np.where(self.active_artist_mask)[0]
        self.matrix_T_filtered = self.matrix.T.tocsr()[self.active_artist_mask]

        self.is_fitted = True
        print(f"CF Recommender fitted.")
        print(f"Matrix: {matrix.shape[0]:,} users x {matrix.shape[1]:,} artists")
        print(f"Active artists (>=5 listeners): {self.active_artist_mask.sum():,}")
        print(f"Reverse artist lookup precomputed: {len(self.idx_to_artist):,} entries")
        return self

    def _get_user_vector(self, user_id: str):
        if user_id not in self.user_enc.classes_:
            return None
        idx = self.user_enc.transform([user_id])[0]
        return self.matrix.getrow(idx)

    def recommend_user_based(
        self,
        user_id: str,
        k: int = 10,
        filter_seen: bool = True
    ) -> pd.DataFrame:

        assert self.is_fitted, "Call fit() first"

        user_vec = self._get_user_vector(user_id)
        if user_vec is None:
            print(f"User '{user_id[:16]}...' not found in interaction matrix.")
            return pd.DataFrame(columns=["artist_name", "cf_score", "recommendation_source"])

        user_idx = self.user_enc.transform([user_id])[0]

        # Sparse dot product — valid cosine similarity because matrix is L2-normalized
        # Dramatically faster than sklearn cosine_similarity which densifies the matrix
        sim_scores = np.asarray(self.matrix.dot(user_vec.T).todense()).flatten()
        sim_scores[user_idx] = -1  # exclude self

        neighbor_indices = np.argsort(sim_scores)[::-1][:self.n_neighbors]
        neighbor_sims = sim_scores[neighbor_indices]

        heard = set()
        if filter_seen:
            heard = set(
                self.interactions_df.loc[
                    self.interactions_df["user_id"] == user_id, "artist_name"
                ].values
            )

        candidate_scores = {}

        for neighbor_idx, sim in zip(neighbor_indices, neighbor_sims):
            if sim <= 0:
                continue

            neighbor_row = self.matrix.getrow(neighbor_idx)
            artist_indices = neighbor_row.indices
            artist_values = neighbor_row.data

            for art_idx, art_val in zip(artist_indices, artist_values):
                # O(1) array lookup instead of O(n) inverse_transform call
                artist_name = self.idx_to_artist[art_idx]
                if artist_name in heard:
                    continue
                if artist_name not in candidate_scores:
                    candidate_scores[artist_name] = 0.0
                candidate_scores[artist_name] += float(sim) * float(art_val)

        if not candidate_scores:
            return pd.DataFrame(columns=["artist_name", "cf_score", "recommendation_source"])

        results = (
            pd.DataFrame(list(candidate_scores.items()), columns=["artist_name", "cf_score"])
            .sort_values("cf_score", ascending=False)
            .head(k)
        )
        results["recommendation_source"] = "user_based_cf"
        return results.reset_index(drop=True)

    def recommend_item_based(
        self,
        user_id: str,
        k: int = 10,
        filter_seen: bool = True
    ) -> pd.DataFrame:

        assert self.is_fitted, "Call fit() first"

        user_vec = self._get_user_vector(user_id)
        if user_vec is None:
            return pd.DataFrame(columns=["artist_name", "cf_score", "recommendation_source"])

        _, seed_artist_indices = user_vec.nonzero()
        seed_weights = np.asarray(user_vec[0, seed_artist_indices]).flatten()

        heard = set()
        if filter_seen:
            heard = set(
                self.interactions_df.loc[
                    self.interactions_df["user_id"] == user_id, "artist_name"
                ].values
            )

        # Top 20 seed artists by user play weight
        top_seed_order = np.argsort(seed_weights)[::-1][:20]
        top_seed_indices = seed_artist_indices[top_seed_order]
        top_seed_weights = seed_weights[top_seed_order]

        candidate_scores = {}

        for seed_idx, seed_weight in zip(top_seed_indices, top_seed_weights):

            # Check if seed artist is in filtered space
            filtered_positions = np.where(self.active_artist_indices == seed_idx)[0]
            if len(filtered_positions) == 0:
                continue  # seed artist too rare to have useful neighbors

            seed_filtered_idx = filtered_positions[0]
            seed_vec = self.matrix_T_filtered.getrow(seed_filtered_idx)

            # Similarity: seed artist vs all active artists in filtered space
            sim_scores = np.asarray(
                self.matrix_T_filtered.dot(seed_vec.T).todense()
            ).flatten()

            # Exclude self in filtered space
            sim_scores[seed_filtered_idx] = -1

            # Top 20 similar artists in filtered space
            top_n_filtered = np.argsort(sim_scores)[::-1][:20]

            for filtered_idx in top_n_filtered:
                sim = float(sim_scores[filtered_idx])
                if sim <= 0:
                    continue

                # Map filtered index back to original artist index
                original_idx = self.active_artist_indices[filtered_idx]

                # O(1) array lookup instead of inverse_transform call
                artist_name = self.idx_to_artist[original_idx]

                if artist_name in heard:
                    continue
                if artist_name not in candidate_scores:
                    candidate_scores[artist_name] = 0.0
                candidate_scores[artist_name] += sim * float(seed_weight)

        if not candidate_scores:
            return pd.DataFrame(columns=["artist_name", "cf_score", "recommendation_source"])

        results = (
            pd.DataFrame(list(candidate_scores.items()), columns=["artist_name", "cf_score"])
            .sort_values("cf_score", ascending=False)
            .head(k)
        )
        results["recommendation_source"] = "item_based_cf"
        return results.reset_index(drop=True)

    def recommend_for_user(self, user_id: str, k: int = 10, filter_seen: bool = True):
        return self.recommend_user_based(user_id, k=k, filter_seen=filter_seen)