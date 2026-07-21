
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from sklearn.preprocessing import normalize


class SVDRecommender:
    """
    Matrix Factorization via Truncated SVD for implicit feedback.

    Decomposes the user-artist interaction matrix R into:
        R ≈ U × S × V^T
    where:
        U : (n_users   × n_factors) — user factor matrix
        S : (n_factors,)            — singular values (importance of each factor)
        V : (n_artists × n_factors) — artist factor matrix

    User and artist embeddings are obtained by absorbing singular
    values into both factor matrices:
        user_factors   = U × sqrt(S)
        artist_factors = V × sqrt(S)

    Why absorb sqrt(S) into both sides:
    The raw U and V matrices are orthonormal — their dot products
    don't reflect the importance of each latent dimension. Absorbing
    sqrt(S) scales each factor dimension by its importance, so that
    dot products between user and artist vectors produce meaningful
    relevance scores.

    Why Truncated SVD (not full SVD):
    Full SVD on a 75K × 145K matrix is computationally infeasible.
    Truncated SVD computes only the top-k singular vectors
    (the k most important latent dimensions), which is both
    feasible and sufficient — the remaining dimensions capture
    noise, not signal.
    """

    def __init__(self, n_factors: int = 100):
        self.n_factors = n_factors
        self.user_factors = None      # shape: (n_users, n_factors)
        self.artist_factors = None    # shape: (n_artists, n_factors)
        self.user_enc = None
        self.artist_enc = None
        self.idx_to_artist = None
        self.interactions_df = None
        self.is_fitted = False

    def fit(
        self,
        matrix: csr_matrix,
        user_enc,
        artist_enc,
        interactions_df: pd.DataFrame
    ):
        """
        Decompose the interaction matrix using truncated SVD.
        """
        self.user_enc = user_enc
        self.artist_enc = artist_enc
        self.idx_to_artist = artist_enc.classes_.tolist()
        self.interactions_df = interactions_df.copy()

        print(f"Running truncated SVD: {matrix.shape} → {self.n_factors} factors...")

        # scipy svds returns smallest singular values by default
        # k must be < min(matrix.shape) - 1
        # Returns U (n_users x k), S (k,), Vt (k x n_artists)
        U, S, Vt = svds(matrix.astype(np.float32), k=self.n_factors)

        # svds returns singular values in ascending order — reverse to descending
        U  = U[:, ::-1]
        S  = S[::-1]
        Vt = Vt[::-1, :]

        # Absorb sqrt of singular values into both factor matrices
        sqrt_S = np.sqrt(S)
        self.user_factors   = U  * sqrt_S          # (n_users, n_factors)
        self.artist_factors = Vt.T * sqrt_S        # (n_artists, n_factors)

        # L2-normalize for cosine similarity recommendations
        self.user_factors   = normalize(self.user_factors,   norm="l2")
        self.artist_factors = normalize(self.artist_factors, norm="l2")

        self.is_fitted = True
        print(f"SVD complete.")
        print(f"User factors:   {self.user_factors.shape}")
        print(f"Artist factors: {self.artist_factors.shape}")
        print(f"Top singular values: {S[:5].round(2)}")
        return self

    def recommend(
        self,
        user_id: str,
        k: int = 10,
        filter_seen: bool = True
    ) -> pd.DataFrame:
        """
        Recommend artists by finding the nearest artist vectors
        to the user's latent factor vector.

        This is a simple dot product (cosine similarity after L2 norm)
        between the user vector and all artist vectors.
        O(n_artists × n_factors) — much faster than memory-based CF.
        """
        assert self.is_fitted, "Call fit() first"

        if user_id not in self.user_enc.classes_:
            return pd.DataFrame(
                columns=["artist_name", "svd_score", "recommendation_source"]
            )

        user_idx = self.user_enc.transform([user_id])[0]
        user_vec = self.user_factors[user_idx]  # shape: (n_factors,)

        # Dot product with all artist vectors — shape: (n_artists,)
        scores = self.artist_factors.dot(user_vec)

        # Filter seen artists
        heard = set()
        if filter_seen:
            heard = set(
                self.interactions_df.loc[
                    self.interactions_df["user_id"] == user_id, "artist_name"
                ].values
            )

        sorted_indices = np.argsort(scores)[::-1]

        results = []
        for idx in sorted_indices:
            artist_name = self.idx_to_artist[idx]
            if artist_name in heard:
                continue
            results.append({
                "artist_name": artist_name,
                "svd_score": round(float(scores[idx]), 4),
                "recommendation_source": "svd_mf"
            })
            if len(results) == k:
                break

        return pd.DataFrame(results)

    def similar_artists(
        self,
        artist_name: str,
        k: int = 10
    ) -> pd.DataFrame:
        """
        Find artists with similar latent factor vectors.
        Useful for item cold start and 'fans also like' features.
        """
        assert self.is_fitted, "Call fit() first"

        if artist_name not in self.artist_enc.classes_:
            print(f"'{artist_name}' not in artist encoder.")
            return pd.DataFrame(columns=["artist_name", "similarity"])

        artist_idx = self.artist_enc.transform([artist_name])[0]
        artist_vec = self.artist_factors[artist_idx]

        scores = self.artist_factors.dot(artist_vec)
        scores[artist_idx] = -1  # exclude self

        top_indices = np.argsort(scores)[::-1][:k]

        return pd.DataFrame({
            "artist_name": [self.idx_to_artist[i] for i in top_indices],
            "similarity":  [round(float(scores[i]), 4) for i in top_indices]
        })