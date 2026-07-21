

import numpy as np
import pandas as pd


class RecommendationRanker:
    """
    Post-hybrid ranking layer implementing:
    1. Novelty re-ranking   — penalize globally popular artists
    2. Diversity re-ranking — Maximal Marginal Relevance (MMR)
       to avoid redundant recommendations
    3. Deduplication        — suppress near-duplicate artist names

    This runs AFTER the hybrid scorer, on the hybrid's candidate pool.
    Input:  scored candidate DataFrame from HybridRecommender.recommend()
    Output: re-ranked top-K DataFrame

    Why MMR for diversity:
    MMR (Maximal Marginal Relevance) is the standard algorithm for
    diversity-aware ranking. At each step it selects the candidate
    that maximizes: lambda * relevance - (1-lambda) * max_similarity_to_selected
    Lambda controls the relevance/diversity tradeoff.
    Lambda=1.0 → pure relevance ranking (same as hybrid score order)
    Lambda=0.0 → pure diversity (ignore relevance, maximize spread)
    Lambda=0.7 → production default (relevance-biased with diversity)
    """

    def __init__(
        self,
        novelty_weight: float = 0.2,
        diversity_lambda: float = 0.7,
        dedup_threshold: float = 0.85
    ):
        """
        Parameters:
            novelty_weight   : how much to penalize popular artists (0=none, 1=full)
            diversity_lambda : MMR tradeoff — higher = more relevance, lower = more diversity
            dedup_threshold  : string similarity threshold for near-duplicate suppression
        """
        self.novelty_weight = novelty_weight
        self.diversity_lambda = diversity_lambda
        self.dedup_threshold = dedup_threshold
        self.popularity_df = None
        self.content_df = None

    def fit(self, popularity_df: pd.DataFrame, content_df: pd.DataFrame):
        """
        Store popularity and content feature tables for novelty
        scoring and diversity computation.
        """
        self.popularity_df = popularity_df.copy()
        self.content_df = content_df.copy()

        # Build artist -> popularity_score lookup
        self.pop_lookup = dict(
            zip(popularity_df["artist_name"], popularity_df["popularity_score"])
        )

        # Build artist -> audio feature vector lookup (for MMR diversity)
        matched = content_df[content_df["has_content_features"]].copy()
        self.audio_lookup = dict(
            zip(
                matched["artist_name"],
                matched[["danceability","energy","loudness","speechiness",
                          "acousticness","instrumentalness","liveness",
                          "valence","tempo"]].values.tolist()
            )
        )
        return self

    def _novelty_score(self, artist_name: str) -> float:
        """
        Novelty = 1 - popularity_score.
        A globally popular artist has low novelty (user likely knows them).
        A rare artist has high novelty (genuine discovery potential).
        Returns 0.5 for artists not in popularity table (neutral).
        """
        pop = self.pop_lookup.get(artist_name, 0.5)
        return 1.0 - pop

    def _apply_novelty(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """
        Blend hybrid score with novelty score.
        final_score = (1 - novelty_weight) * hybrid_score
                    + novelty_weight * novelty_score
        """
        candidates = candidates.copy()
        candidates["novelty_score"] = candidates["artist_name"].apply(
            self._novelty_score
        )
        candidates["ranked_score"] = (
            (1 - self.novelty_weight) * candidates["hybrid_score"] +
            self.novelty_weight * candidates["novelty_score"]
        )
        return candidates.sort_values("ranked_score", ascending=False)

    def _dedup(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """
        Remove near-duplicate artist names.
        Uses character-level Jaccard similarity on artist name tokens.

        Why Jaccard on tokens (not edit distance):
        Edit distance is O(n*m) per pair — too slow for a ranking loop.
        Token Jaccard is O(tokens) and catches the main duplication
        pattern in this dataset: 'miranda' vs 'miranda!' vs 'miranda x'.
        """
        def jaccard(a: str, b: str) -> float:
            set_a = set(a.lower().split())
            set_b = set(b.lower().split())
            if not set_a or not set_b:
                return 0.0
            return len(set_a & set_b) / len(set_a | set_b)

        seen = []
        keep = []

        for _, row in candidates.iterrows():
            name = row["artist_name"]
            is_dup = False
            for kept_name in seen:
                if jaccard(name, kept_name) >= self.dedup_threshold:
                    is_dup = True
                    break
            if not is_dup:
                seen.append(name)
                keep.append(row)

        return pd.DataFrame(keep).reset_index(drop=True)

    def _mmr_rerank(
        self,
        candidates: pd.DataFrame,
        k: int
    ) -> pd.DataFrame:
        """
        Maximal Marginal Relevance re-ranking for diversity.

        Algorithm:
        1. Start with empty selected set S
        2. At each step, pick the candidate i that maximizes:
           MMR(i) = lambda * ranked_score(i)
                  - (1-lambda) * max_{j in S} similarity(i, j)
        3. Add i to S, repeat until |S| = k

        Similarity between two artists:
        - If both have audio features: cosine similarity of feature vectors
        - Otherwise: 0.0 (treat as dissimilar — safe default)

        Why this matters:
        Without MMR, the top-10 might be 10 Latin pop artists with
        nearly identical audio profiles. MMR ensures that once one
        Latin pop artist is selected, the next pick is penalized for
        being too similar — pushing the algorithm toward selecting
        an artist from a different sub-cluster.
        """
        def audio_vec(artist: str):
            vec = self.audio_lookup.get(artist)
            if vec is None:
                return None
            return np.array(vec, dtype=np.float32)

        def cosine(a, b):
            if a is None or b is None:
                return 0.0
            denom = np.linalg.norm(a) * np.linalg.norm(b)
            if denom < 1e-9:
                return 0.0
            return float(np.dot(a, b) / denom)

        remaining = candidates.reset_index(drop=True)
        selected = []
        selected_vecs = []

        for _ in range(min(k, len(remaining))):
            best_idx = None
            best_score = -np.inf

            for i, row in remaining.iterrows():
                relevance = row["ranked_score"]

                # Max similarity to already-selected artists
                vec_i = audio_vec(row["artist_name"])
                if selected_vecs:
                    max_sim = max(cosine(vec_i, v) for v in selected_vecs)
                else:
                    max_sim = 0.0

                mmr_score = (
                    self.diversity_lambda * relevance -
                    (1 - self.diversity_lambda) * max_sim
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            if best_idx is None:
                break

            selected.append(remaining.loc[best_idx])
            selected_vecs.append(audio_vec(remaining.loc[best_idx, "artist_name"]))
            remaining = remaining.drop(index=best_idx)

        return pd.DataFrame(selected).reset_index(drop=True)

    def rank(
        self,
        candidates: pd.DataFrame,
        k: int = 10,
        use_novelty: bool = True,
        use_diversity: bool = True,
        use_dedup: bool = True
    ) -> pd.DataFrame:
        """
        Full ranking pipeline:
        1. Deduplication (remove near-duplicate artist names)
        2. Novelty re-scoring (penalize globally popular artists)
        3. MMR diversity re-ranking (maximize list diversity)

        Parameters:
            candidates   : output of HybridRecommender.recommend()
            k            : final number of recommendations to return
            use_novelty  : toggle novelty re-scoring
            use_diversity: toggle MMR diversity re-ranking
            use_dedup    : toggle near-duplicate suppression
        """
        df = candidates.copy()

        if use_dedup:
            before = len(df)
            df = self._dedup(df)
            after = len(df)
            if before != after:
                print(f"Dedup removed {before - after} near-duplicate artists")

        if use_novelty:
            df = self._apply_novelty(df)
        else:
            df["novelty_score"] = 0.0
            df["ranked_score"] = df["hybrid_score"]

        if use_diversity:
            df = self._mmr_rerank(df, k=k)
        else:
            df = df.head(k)

        return df[[
            "artist_name", "ranked_score", "hybrid_score",
            "novelty_score"
        ]].reset_index(drop=True)