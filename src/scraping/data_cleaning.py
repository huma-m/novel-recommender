import logging
from collections import Counter
from itertools import chain
from typing import List, Set, Optional
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_UNRELATED = [
    "Adapted to Drama CD", "Adapted to Manhua", "Adapted to Drama",
    "Adapted to Anime", "Adapted to Manhwa", "Multiple POV",
    "Unreliable Narrator", "Cute Story"
]

def compute_tag_counts(df: pd.DataFrame) -> Counter:
    logger.info("Computing tag counts")
    return Counter(chain.from_iterable(df["tags"].dropna().tolist()))

def top_tags_df(tag_counts: Counter, min_count: int = 10) -> pd.DataFrame:
    logger.info("Building top tags DataFrame with min_count=%s", min_count)
    items = [(t, c) for t, c in tag_counts.items() if c > min_count]
    df = pd.DataFrame(items, columns=["tag", "count"]).sort_values("count", ascending=False)
    return df.reset_index(drop=True)

def filter_to_top_tags(df: pd.DataFrame, top_tags: Set[str]) -> pd.DataFrame:
    logger.info("Filtering tags to top tags (size=%d)", len(top_tags))
    df["tags"] = df["tags"].apply(lambda lst: [t for t in lst if t in top_tags] if isinstance(lst, list) else [])
    return df

def remove_unrelated(df: pd.DataFrame, unrelated = None) -> pd.DataFrame:
    unrelated = set(unrelated or DEFAULT_UNRELATED)
    logger.info("Removing %d unrelated tags", len(unrelated))
    df["tags"] = df["tags"].apply(lambda lst: [t for t in lst if t not in unrelated and '*' not in t])
    return df

def cleaning_pipeline(
    df: pd.DataFrame,
    min_tag_count: int = 10,
    unrelated: Optional[List[str]] = None,
):
    tag_counts = compute_tag_counts(df)
    top = top_tags_df(tag_counts, min_tag_count)
    df = filter_to_top_tags(df, set(top["tag"]))
    df = remove_unrelated(df, unrelated)
    return df
