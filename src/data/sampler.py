# src/data/sampler.py
import pandas as pd

def stratified_sample_users(interactions_df: pd.DataFrame, n_samples: int, random_seed: int = 42) -> pd.DataFrame:
    
    user_totals = interactions_df.groupby("user_id")["plays"].sum().reset_index()
    user_totals.columns = ["user_id", "total_plays"]

    bins = [0, 100, 500, 2000, 10000, float("inf")]
    labels = ["0-100", "101-500", "501-2000", "2001-10000", "10000+"]
    user_totals["bucket"] = pd.cut(user_totals["total_plays"], bins=bins, labels=labels)

    sampled_ids = user_totals.groupby("bucket", group_keys=False).apply(
        lambda x: x.sample(
            n=max(1, round(n_samples * len(x) / len(user_totals))),
            random_state=random_seed
        )
    )["user_id"]

    return interactions_df[interactions_df["user_id"].isin(sampled_ids)].reset_index(drop=True)