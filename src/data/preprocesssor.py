import numpy as np
import pandas as pd
import pickle
from sklearn.preprocessing import LabelEncoder, normalize
from scipy.sparse import csr_matrix

def build_interaction_matrix(interactions_df: pd.DataFrame) -> tuple:
    user_enc=LabelEncoder()
    artist_enc=LabelEncoder()
    user_idx=user_enc.fit_transform(interactions_df["user_id"])
    artist_idx=artist_enc.fit_transform(interactions_df["artist_name"])

    values=np.log1p(interactions_df["plays"].values).astype(np.float32)

    n_users= len(user_enc.classes_)
    n_artists=len(artist_enc.classes_)

    matrix=csr_matrix((values,(user_idx,artist_idx)),
                      shape=(n_users,n_artists))
    
    matrix = normalize(matrix, norm="l2", axis=1)

    return matrix,user_enc,artist_enc

def build_popularity_scores(interactions_df: pd.DataFrame) -> pd.DataFrame:
    
    pop = interactions_df.groupby("artist_name").agg(
        total_plays=("plays", "sum"),
        unique_listeners=("user_id", "nunique"),
        avg_plays_per_listener=("plays", "mean"),
    ).reset_index()

   
    pop["popularity_score"] = (
        pop["unique_listeners"].rank(method="average") / len(pop)
    )

    return pop.sort_values("popularity_score", ascending=False).reset_index(drop=True)