from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import os
import numpy as np

CACHE_DIR = "data/cache"
os.makedirs(CACHE_DIR, exist_ok=True)
TAG_SIMILARITY_CACHE = os.path.join(CACHE_DIR, "tag_similarity.npy")
DESC_EMBEDDING_CACHE = os.path.join(CACHE_DIR, "desc_embedding.npy")
DESC_SIMILARITY_CACHE = os.path.join(CACHE_DIR, "desc_similarity.npy")

def add_cluster_column(novels, tag_clusters):
    novels['clusters'] = novels['tags'].apply(
        lambda tags:[tag_clusters[t] for t in tags if t in tag_clusters]
        )
    return novels

def compute_tag_similarity(novels):
    if os.path.exists(TAG_SIMILARITY_CACHE):
        return np.load(TAG_SIMILARITY_CACHE)
    
    mlb = MultiLabelBinarizer()
    tag_matrix = mlb.fit_transform(novels['clusters'])
    similarity = cosine_similarity(tag_matrix)
    np.save(TAG_SIMILARITY_CACHE, similarity)
    return similarity

def compute_desc_similarity(novels):
    if os.path.exists(DESC_SIMILARITY_CACHE):
        return np.load(DESC_SIMILARITY_CACHE)
    
    if os.path.exists(DESC_EMBEDDING_CACHE):
        embedding = np.load(DESC_EMBEDDING_CACHE)
    else:    
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embedding = model.encode(novels['description'].tolist())
        np.save(DESC_EMBEDDING_CACHE, embedding)
    similarity = cosine_similarity(embedding)
    np.save(DESC_SIMILARITY_CACHE, similarity)
    return similarity

def combine_similarities(tag_similarity, desc_similarity, tag_weight=0.4, desc_weight=0.6):
    assert abs(tag_weight + desc_weight - 1.0) < 1e-6, "Weights must sum to 1"
    combined = (tag_similarity * tag_weight) + (desc_similarity * desc_weight)
    return combined

def get_novel_data(novels,idx):
    novel = novels.iloc[idx]
    return {
        'title': novel['title'],
        'genres': novel['genres'],
        'tags': novel['tags'],
        'description': novel['description'],
        'link': novel['link']
    }
    
def recommend_novels(title, novels, similarity, top_n=5, min_similarity=0.2):
    title = title.lower().strip()
    try:
        idx = novels[novels['title'].str.lower() == title].index[0]
    except IndexError:
        closest = novels[novels['title'].str.lower().str.contains(title)]
        if len(closest) == 0:
            raise ValueError(f"No match found")
        idx = closest.index[0]
        print(f"Using closest match: {novels.iloc[idx]['title']}")
        
    scores = list(enumerate(similarity[idx]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)
    
    recommendations = []
    for i, score in scores[1:]:
        if score < min_similarity: 
            continue
        if len(recommendations) >= top_n:
            break
        rec = get_novel_data(novels,i)
        rec['similarity'] = round(score, 3)
        recommendations.append(rec)
    
    return recommendations