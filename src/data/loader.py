import pandas as pd

def load_lastfm_interactions(path: str) -> pd.DataFrame:
    """
    Load Last.fm user-artist play counts.
    Columns: user_id, artist_mbid, artist_name, plays
    """
    df = pd.read_csv(
        path,
        sep="\t",
        header=None,
        names=["user_id", "artist_mbid", "artist_name", "plays"],
        usecols=["user_id", "artist_name", "plays"],  # drop mbid, mostly redundant w/ name, #load only specific cols in df
    )
    # Drop rows with missing artist names or zero/negative plays
    df = df.dropna(subset=["artist_name"])
    df = df[df["plays"] > 0]
    return df

def load_lastfm_profiles(path: str) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep="\t",
        header=None,
        names=["user_id", "gender", "age", "country", "signup_date"],
    )
    return df

def load_spotify_tracks(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Standard columns in this dataset: track_id, artists, album_name, track_name,
    # popularity, duration_ms, explicit, danceability, energy, key, loudness, mode,
    # speechiness, acousticness, instrumentalness, liveness, valence, tempo,
    # time_signature, track_genre
    return df