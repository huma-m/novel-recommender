import pandas as pd
from src.database.database_opr import NovelDB

_db = None
def get_db():
    global _db
    if _db is None:
        _db = NovelDB("data/novels_db.db")
    return _db

def load_data(cluster_path="data/processed/tag_clusters.csv"):
    db = get_db()
    novels = db.get_all_novels()
    tag_clusters = pd.read_csv(cluster_path)
    tag_clusters_dict = dict(zip(tag_clusters['tag'], tag_clusters['cluster']))
    return novels, tag_clusters_dict

def search_novels(query: str, limit: int = 10):
    db = get_db()
    return db.search_novels_by_title(query, limit)

def get_novel_by_title(title: str):
    db = get_db()
    return db.get_novel_by_title(title)