from sklearn.metrics.pairwise import cosine_similarity
from src.data_loader import load_data
import numpy as np


def compute_similarities(novels, tag_weight=0.4, desc_weight=0.6):
    tag_matrix = np.vstack(novels["tag_embedding"].values)
    desc_matrix = np.vstack(novels["desc_embedding"].values)

    tag_similarity = cosine_similarity(tag_matrix)
    desc_similarity = cosine_similarity(desc_matrix)
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

if __name__ == "__main__":
    novels = load_data()
    similarity = compute_similarities(novels, 0.5, 0.5)
    recs = recommend_novels("Kaleidoscope of Death", novels, similarity, 10)
    for i in recs:
        print(i.get('title'))