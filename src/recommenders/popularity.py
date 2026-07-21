import pandas as pd
import numpy as np


class PopularityRecommender:

    def __init__(self):
        self.popularity_df = None #stores popularity table
        self.interactions_df = None # stores users listning history
        self.is_fitted = False

    def fit(self, popularity_df: pd.DataFrame, interactions_df: pd.DataFrame):
        
        self.popularity_df = popularity_df.copy()
        self.interactions_df = interactions_df.copy()
        self.is_fitted = True
        print(f"PopularityRecommender fitted on {len(popularity_df):,} artists.")
        return self

    def recommend(
        self,
        user_id: str = None,
        k: int = 10,
        filter_seen: bool = True
    ) -> pd.DataFrame:
        
        assert self.is_fitted, "Call fit() before recommend()"

        candidates = self.popularity_df.copy()

        
        if user_id is not None and filter_seen:
            heard = set(
                self.interactions_df.loc[
                    self.interactions_df["user_id"] == user_id, "artist_name"
                ].values
            )
            candidates = candidates[~candidates["artist_name"].isin(heard)]

        top_k = candidates.head(k)[
            ["artist_name", "popularity_score", "unique_listeners"]
        ].copy()

        
        top_k["recommendation_source"] = (
            "popularity_cold_start" if user_id is None else "popularity"
        )

        return top_k.reset_index(drop=True)

    def recommend_cold_start(self, k: int = 10) -> pd.DataFrame:
        
        return self.recommend(user_id=None, k=k, filter_seen=False)