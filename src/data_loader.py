import pandas as pd

def load_data(novel_path="data/processed/novel_details_cleaned.json", cluster_path="data/processed/tag_clusters.csv"):
    novels = pd.read_json(novel_path)
    tag_clusters = pd.read_csv(cluster_path)
    tag_clusters_dict = dict(zip(tag_clusters['tag'], tag_clusters['cluster']))
    return novels, tag_clusters_dict