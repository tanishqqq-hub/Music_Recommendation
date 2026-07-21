import pandas as pd
import numpy as np
import re
from sklearn.preprocessing import StandardScaler


AUDIO_FEATURES = [
    "danceability", "energy", "loudness", "speechiness",
    "acousticness", "instrumentalness", "liveness", "valence", "tempo"
]


def normalize_artist_name(name: str) -> str:
    
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def build_content_features(
    tracks_df: pd.DataFrame,
    popularity_df: pd.DataFrame
) -> pd.DataFrame:
    

    
    tracks = tracks_df.copy()
    tracks["artist_norm"] = (
        tracks["artists"]
        .str.split(r"[;,]")
        .str[0]
        .apply(normalize_artist_name)
    )

    
    artist_features = (
        tracks.groupby("artist_norm")[AUDIO_FEATURES]
        .mean()
        .reset_index()
    )

    
    popularity_df = popularity_df.copy()
    popularity_df["artist_norm"] = popularity_df["artist_name"].apply(normalize_artist_name)

    
    merged = popularity_df.merge(artist_features, on="artist_norm", how="left")

    
    merged["has_content_features"] = merged[AUDIO_FEATURES[0]].notna()

    
    scaler = StandardScaler()
    has_features = merged["has_content_features"]
    merged.loc[has_features, AUDIO_FEATURES] = scaler.fit_transform(
        merged.loc[has_features, AUDIO_FEATURES]
    )

    
    merged[AUDIO_FEATURES] = merged[AUDIO_FEATURES].fillna(0)

    return merged, scaler