from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics.pairwise import cosine_similarity

def add_cluster_column(novels, tag_clusters):
    novels['clusters'] = novels['tags'].apply(
        lambda tags: {
            tag_clusters[t] for t in tags if t in tag_clusters
            }
    )
    return novels

def compute_tag_similarity(novels):
    mlb = MultiLabelBinarizer()
    tag_matrix = mlb.fit_transform(novels['clusters'])
    similarity = cosine_similarity(tag_matrix)
    return similarity

def get_novel_data(novels,idx):
    novel = novels.iloc[idx]
    return {
        'title': novel['title'],
        'genre': novel['genres'],
        'tags': novel['tags'],
        'description': novel['description'],
        'link': novel['link']
    }
    
def recommend_novels(title, novels, similarity, top_n=5, min_similarity=0.2):
    title = title.lower()
    try:
        idx = novels[novels['title'].str.lower() == title].index[0]
    except IndexError:
        closest = novels[novels['title'].str.lower().str.contains(title)]
        if len(closest) == 0:
            raise ValueError(f"No match found")
        idx = closest.index[0]
        print(f"Using closest match: {novels.iloc[0]['title']}")
        
    scores = list(enumerate(similarity[idx]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)
    
    recommendations = []
    for i, score in scores[1:]:
        if score < min_similarity or len(recommendations) >= top_n:
            break
        rec = get_novel_data(novels,i)
        rec['similarity'] = round(score, 3)
        recommendations.append(rec)
    
    return recommendations