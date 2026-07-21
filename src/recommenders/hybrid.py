# src/recommenders/hybrid.py

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


class HybridRecommender:
    """
    Weighted hybrid recommendation engine combining:
    - Popularity score     (cold start signal, global appeal)
    - SVD score            (personalized latent factor signal)
    - Content-based score  (audio feature similarity signal)

    Design principle: each engine contributes where it's strongest.
    Scores are min-max normalized before weighting so no single
    engine dominates due to raw score scale differences.

    Fallback logic:
    - If SVD unavailable (user not in matrix): weight shifts to popularity
    - If content features unavailable (artist not matched): cb_score = 0,
      remaining weight redistributed to SVD and popularity proportionally
    """

    def __init__(
        self,
        w_popularity: float = 0.1,
        w_svd: float = 0.6,
        w_content: float = 0.3
    ):
        assert abs(w_popularity + w_svd + w_content - 1.0) < 1e-6, \
            "Weights must sum to 1.0"

        self.w_popularity = w_popularity
        self.w_svd = w_svd
        self.w_content = w_content

        self.pop_rec = None
        self.svd_rec = None
        self.cb_rec = None
        self.is_fitted = False

    def fit(self, pop_rec, svd_rec, cb_rec):
        """
        Store fitted engine instances.
        Each engine must already be fitted before passing here.
        """
        self.pop_rec = pop_rec
        self.svd_rec = svd_rec
        self.cb_rec = cb_rec
        self.is_fitted = True
        print("HybridRecommender fitted with engines:")
        print(f"  Popularity  weight: {self.w_popularity}")
        print(f"  SVD         weight: {self.w_svd}")
        print(f"  Content     weight: {self.w_content}")
        return self

    def _normalize(self, series: pd.Series) -> pd.Series:
        """
        Min-max normalize a score series to [0, 1].
        If all values are identical (zero variance), return zeros.
        This prevents division by zero when an engine returns
        uniform scores.
        """
        min_val = series.min()
        max_val = series.max()
        if max_val - min_val < 1e-9:
            return pd.Series(np.zeros(len(series)), index=series.index)
        return (series - min_val) / (max_val - min_val)

    def recommend(
        self,
        user_id: str = None,
        k: int = 10,
        candidate_pool: int = 100
    ) -> pd.DataFrame:
        """
        Generate hybrid recommendations.

        Strategy:
        1. Get top-candidate_pool candidates from each engine
        2. Build a unified candidate table (union of all candidates)
        3. For each candidate, collect scores from all engines
           (0.0 if engine didn't surface that candidate)
        4. Normalize each score column to [0, 1]
        5. Compute weighted hybrid score
        6. Return top-k by hybrid score

        Why candidate_pool >> k:
        Each engine surfaces different artists. Taking top-100 from
        each engine before combining ensures the hybrid has enough
        candidates to find the best cross-engine consensus, while
        keeping computation bounded.

        Parameters:
            user_id        : target user (None = cold start)
            k              : final number of recommendations
            candidate_pool : how many candidates to pull from each engine
        """
        assert self.is_fitted, "Call fit() first"

        # --- Popularity candidates (always available) ---
        pop_recs = self.pop_rec.recommend(
            user_id=user_id,
            k=candidate_pool,
            filter_seen=True
        )[["artist_name", "popularity_score"]].copy()
        pop_recs.columns = ["artist_name", "pop_score"]

        # --- SVD candidates ---
        svd_available = (
            user_id is not None and
            user_id in self.svd_rec.user_enc.classes_
        )

        if svd_available:
            svd_recs = self.svd_rec.recommend(
                user_id, k=candidate_pool, filter_seen=True
            )[["artist_name", "svd_score"]].copy()
        else:
            # Cold start: no SVD signal available
            svd_recs = pd.DataFrame(columns=["artist_name", "svd_score"])

        # --- Content-based candidates ---
        profile = self.cb_rec._build_user_profile(user_id)
        cb_available = (user_id is not None and profile is not None)

        if cb_available:
            cb_recs = self.cb_rec.recommend_for_user(
                user_id, k=candidate_pool, filter_seen=True
            )[["artist_name", "similarity_score"]].copy()
            cb_recs.columns = ["artist_name", "cb_score"]
        else:
            cb_recs = pd.DataFrame(columns=["artist_name", "cb_score"])

        # --- Build unified candidate table ---
        all_artists = set(pop_recs["artist_name"])
        if not svd_recs.empty:
            all_artists |= set(svd_recs["artist_name"])
        if not cb_recs.empty:
            all_artists |= set(cb_recs["artist_name"])

        candidates = pd.DataFrame({"artist_name": list(all_artists)})

        # Merge scores — missing = 0.0 (engine didn't surface this artist)
        candidates = candidates.merge(pop_recs, on="artist_name", how="left")
        candidates = candidates.merge(svd_recs, on="artist_name", how="left")
        candidates = candidates.merge(cb_recs,  on="artist_name", how="left")
        candidates = candidates.fillna(0.0)

        # --- Normalize each score to [0, 1] ---
        candidates["pop_score_norm"] = self._normalize(candidates["pop_score"])
        candidates["svd_score_norm"] = self._normalize(candidates["svd_score"])
        candidates["cb_score_norm"]  = self._normalize(candidates["cb_score"])

        # --- Adjust weights if engines unavailable ---
        w_pop = self.w_popularity
        w_svd = self.w_svd
        w_cb  = self.w_content

        if not svd_available and not cb_available:
            # Cold start: popularity only
            w_pop, w_svd, w_cb = 1.0, 0.0, 0.0
        elif not svd_available:
            # No SVD: redistribute SVD weight to popularity and content
            w_pop = self.w_popularity + self.w_svd * 0.5
            w_cb  = self.w_content    + self.w_svd * 0.5
            w_svd = 0.0
        elif not cb_available:
            # No content features: redistribute CB weight to SVD and popularity
            w_svd = self.w_svd        + self.w_content * 0.7
            w_pop = self.w_popularity + self.w_content * 0.3
            w_cb  = 0.0

        # --- Compute hybrid score ---
        candidates["hybrid_score"] = (
            w_pop * candidates["pop_score_norm"] +
            w_svd * candidates["svd_score_norm"] +
            w_cb  * candidates["cb_score_norm"]
        )

        # --- Final ranking ---
        top_k = (
            candidates.sort_values("hybrid_score", ascending=False)
            .head(k)
            .reset_index(drop=True)
        )

        top_k["recommendation_source"] = "hybrid"

        return top_k[[
            "artist_name", "hybrid_score",
            "pop_score_norm", "svd_score_norm", "cb_score_norm",
            "recommendation_source"
        ]]