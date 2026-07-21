# src/api/recommender.py

import pickle
import numpy as np
import pandas as pd
import yaml
from scipy.sparse import load_npz
from pathlib import Path


class RecommenderService:
    """
    Loads all fitted recommender artifacts at startup.
    Exposes inference methods for each endpoint.
    Single instance shared across all API requests.
    """

    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config_path = Path(config_path).expanduser().resolve()

        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)

        self._load_artifacts()

    def _load_artifacts(self):
        cfg = self.config["artifacts"]
        project_root = self.config_path.parent.parent

        def resolve_artifact(path_value: str) -> Path:
            artifact_path = Path(path_value)
            if artifact_path.is_absolute():
                return artifact_path
            return (project_root / artifact_path).resolve()

        print("Loading recommender artifacts...")

        with open(resolve_artifact(cfg["svd_recommender"]), "rb") as f:
            self.svd_rec = pickle.load(f)

        with open(resolve_artifact(cfg["cb_recommender"]), "rb") as f:
            self.cb_rec = pickle.load(f)

        with open(resolve_artifact(cfg["hybrid_recommender"]), "rb") as f:
            self.hybrid_rec = pickle.load(f)

        with open(resolve_artifact(cfg["ranker"]), "rb") as f:
            self.ranker = pickle.load(f)

        self.popularity_df = pd.read_parquet(resolve_artifact(cfg["artist_popularity"]))
        self.interactions  = pd.read_parquet(resolve_artifact(cfg["interactions"]))

        # Popularity recommender reconstructed from loaded artifacts
        from src.recommenders.popularity import PopularityRecommender
        self.pop_rec = PopularityRecommender()
        self.pop_rec.fit(self.popularity_df, self.interactions)

        self.total_artists = len(self.popularity_df)
        self.total_users   = self.interactions["user_id"].nunique()

        print(f"Loaded. Artists: {self.total_artists:,} | Users: {self.total_users:,}")

    def get_similar_artists(self, artist_name: str, k: int = 10):
        # Try SVD first (latent space similarity)
        result = self.svd_rec.similar_artists(artist_name, k=k)
        if not result.empty:
            return result.rename(columns={"similarity": "score"}), "svd"

        # Fall back to content-based
        result = self.cb_rec.similar_artists(artist_name, k=k)
        if not result.empty:
            return result.rename(columns={"similarity_score": "score"}), "content_based"

        return pd.DataFrame(columns=["artist_name", "score"]), "none"

    def get_recommendations(self, user_id: str, k: int = 10, mode: str = "hybrid"):
        if mode == "hybrid":
            candidates = self.hybrid_rec.recommend(
                user_id=user_id, k=50, candidate_pool=100
            )
            ranked = self.ranker.rank(candidates, k=k)
            results = ranked[["artist_name", "ranked_score"]].copy()
            results.columns = ["artist_name", "score"]
            return results, "hybrid"

        elif mode == "svd":
            results = self.svd_rec.recommend(user_id=user_id, k=k, filter_seen=True)
            results = results[["artist_name", "svd_score"]].copy()
            results.columns = ["artist_name", "score"]
            return results, "svd"

        elif mode == "content":
            results = self.cb_rec.recommend_for_user(user_id=user_id, k=k, filter_seen=True)
            results = results[["artist_name", "similarity_score"]].copy()
            results.columns = ["artist_name", "score"]
            return results, "content_based"

        elif mode == "popularity":
            results = self.pop_rec.recommend(user_id=user_id, k=k, filter_seen=True)
            results = results[["artist_name", "popularity_score"]].copy()
            results.columns = ["artist_name", "score"]
            return results, "popularity"

        return pd.DataFrame(columns=["artist_name", "score"]), "none"

    def get_cold_start(self, k: int = 10):
        results = self.pop_rec.recommend_cold_start(k=k)
        results = results[["artist_name", "popularity_score"]].copy()
        results.columns = ["artist_name", "score"]
        return results, "popularity_cold_start"