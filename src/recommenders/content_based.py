import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


AUDIO_FEATURES = [
    "danceability", "energy", "loudness", "speechiness",
    "acousticness", "instrumentalness", "liveness", "valence", "tempo"
]


class ContentBasedRecommender:
    

    def __init__(self):
        self.content_df = None        # full artist table with features + flags
        self.feature_matrix = None    # numpy array, shape (n_matched, 9)
        self.matched_artists = None   # artist names corresponding to matrix rows
        self.similarity_matrix = None # precomputed (n_matched x n_matched) cosine sim
        self.interactions_df = None   # stores listning history
        self.is_fitted = False

    def fit(
        self,
        content_df: pd.DataFrame,
        interactions_df: pd.DataFrame
    ):
        
        
        matched = content_df[content_df["has_content_features"]].copy()
        matched = matched.reset_index(drop=True)

        self.matched_artists = matched["artist_name"].values
        self.feature_matrix = matched[AUDIO_FEATURES].values.astype(np.float32)
        self.content_df = content_df.copy()
        self.interactions_df = interactions_df.copy()

        
        print(f"Computing similarity matrix for {len(self.matched_artists):,} artists...")
        self.similarity_matrix = cosine_similarity(self.feature_matrix)
        print(f"Similarity matrix shape: {self.similarity_matrix.shape}")
        print(f"Memory usage: {self.similarity_matrix.nbytes / 1e6:.1f} MB")

        self.is_fitted = True
        return self

    def _get_artist_index(self, artist_name: str):
        
        matches = np.where(self.matched_artists == artist_name)[0]
        if len(matches) == 0:
            return None
        return matches[0]

    def similar_artists(
        self,
        artist_name: str,
        k: int = 10,
        filter_input: bool = True
    ) -> pd.DataFrame:
        
        assert self.is_fitted, "Call fit() first"

        idx = self._get_artist_index(artist_name)

        if idx is None:
            
            print(f"'{artist_name}' has no content features. "
                  f"Covered artists: {len(self.matched_artists):,} / "
                  f"{len(self.content_df):,} total.")
            return pd.DataFrame(columns=["artist_name", "similarity_score"])

        
        sim_scores = self.similarity_matrix[idx]

       
        sorted_indices = np.argsort(sim_scores)[::-1]

        results = []
        for i in sorted_indices:
            if filter_input and i == idx:
                continue
            results.append({
                "artist_name": self.matched_artists[i],
                "similarity_score": round(float(sim_scores[i]), 4)
            })
            if len(results) == k:
                break

        return pd.DataFrame(results)

    def _build_user_profile(self, user_id: str) -> np.ndarray:
        
        user_interactions = self.interactions_df[
            self.interactions_df["user_id"] == user_id
        ].copy()

        if user_interactions.empty:
            return None

        
        user_interactions = user_interactions[
            user_interactions["artist_name"].isin(self.matched_artists)
        ]

        if user_interactions.empty:
            return None

        
        profile_vector = np.zeros(len(AUDIO_FEATURES), dtype=np.float32)
        total_weight = 0.0

        for _, row in user_interactions.iterrows():
            idx = self._get_artist_index(row["artist_name"])
            if idx is None:
                continue
            weight = np.log1p(row["plays"])
            profile_vector += weight * self.feature_matrix[idx]
            total_weight += weight

        if total_weight == 0:
            return None

        return profile_vector / total_weight

    def recommend_for_user(
        self,
        user_id: str,
        k: int = 10,
        filter_seen: bool = True
    ) -> pd.DataFrame:
        
        assert self.is_fitted, "Call fit() first"

        profile = self._build_user_profile(user_id)

        if profile is None:
            print(f"User '{user_id[:12]}...' has no artists with content features. "
                  f"Cannot generate content-based recommendations.")
            return pd.DataFrame(
                columns=["artist_name", "similarity_score", "recommendation_source"]
            )

        
        sim_scores = cosine_similarity(
            profile.reshape(1, -1),
            self.feature_matrix
        )[0]  
        heard = set()
        if filter_seen:
            heard = set(
                self.interactions_df.loc[
                    self.interactions_df["user_id"] == user_id, "artist_name"
                ].values
            )

        sorted_indices = np.argsort(sim_scores)[::-1]

        results = []
        for i in sorted_indices:
            artist = self.matched_artists[i]
            if artist in heard:
                continue
            results.append({
                "artist_name": artist,
                "similarity_score": round(float(sim_scores[i]), 4),
                "recommendation_source": "content_based"
            })
            if len(results) == k:
                break

        return pd.DataFrame(results)