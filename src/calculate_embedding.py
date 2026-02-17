from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
from collections import Counter
import math
import logging

from src.database.database_helper import NovelDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GENERIC_TAGS = ["Calm Protagonist", "Clever Protagonist", "Cold Love Interests", 
                "Devoted Love Interests", "Doting Love Interests", "Handsome Male Lead", 
                "Hard-Working Protagonist", "Love Interest Falls in Love First", "Male Protagonist", 
                "Protagonist Strong from the Start", "Strong Love Interests",]

def compute_idf(novels, generic_tags):
    tag_counter = Counter()
    total = len(novels)

    for n in novels:
        if isinstance(n.tags, list):
            filtered = set(t for t in n.tags if t not in generic_tags)
            tag_counter.update(filtered)

    idf = {
        tag: math.log(total / (1 + count))
        for tag, count in tag_counter.items()
    }

    return idf

def store_embeddings():
    db = NovelDB()
    novels = db.get_missing_embedding()
    if not novels:
        logger.info("No novels missing embeddings")
        return        
 
    tag_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    logger.info("Computing tag embedding")
    all_unique_tags = set()

    for n in novels:
        if isinstance(n.tags, list):
            filtered = [t for t in n.tags if t not in GENERIC_TAGS]
            all_unique_tags.update(filtered)

    all_unique_tags = list(all_unique_tags)

    logger.info(f"Encoding {len(all_unique_tags)} unique tags in one batch")
    tag_vectors = tag_model.encode(
        all_unique_tags,
        normalize_embeddings=True,
        batch_size=128,
        show_progress_bar=True
    )

    tag_to_vec = {
        tag: vec for tag, vec in zip(all_unique_tags, tag_vectors)
    }

    idf_dict = compute_idf(novels, GENERIC_TAGS)

    tag_dim = tag_model.get_sentence_embedding_dimension()
    if tag_dim is None:
        raise ValueError("Could not determine embedding dimension.")
    tag_dim = int(tag_dim)

    all_tag_embeddings = []

    for n in novels:
        if not isinstance(n.tags, list):
            all_tag_embeddings.append(np.zeros(tag_dim, dtype=np.float32))
            continue

        filtered = [t for t in n.tags if t not in GENERIC_TAGS]

        if not filtered:
            all_tag_embeddings.append(np.zeros(tag_dim, dtype=np.float32))
            continue

        tag_vecs = np.array([tag_to_vec[t] for t in filtered])
        weights = np.array(
            [idf_dict.get(t, 0.0) for t in filtered],
            dtype=np.float32
        ).reshape(-1, 1)

        weighted = tag_vecs * weights
        novel_vec = weighted.sum(axis=0) / (weights.sum() + 1e-8)

        norm = np.linalg.norm(novel_vec)
        if norm > 0:
            novel_vec = novel_vec / norm

        all_tag_embeddings.append(novel_vec.astype(np.float32))

    tag_embedding = np.vstack(all_tag_embeddings)

    logger.info("Computing desc embedding")
    desc_model = SentenceTransformer('all-mpnet-base-v2')
    descriptions = [n.description.lower() for n in novels]
    desc_embedding = desc_model.encode(descriptions, 
                                       normalize_embeddings=True, 
                                       batch_size=64, 
                                       show_progress_bar=True)
    
    results_df = pd.DataFrame({
        'id': [n.id for n in novels],
        'tag_embedding': tag_embedding.tolist(),
        'desc_embedding': desc_embedding.tolist() 
    })
    
    db.store_embeddings(results_df)
    logger.info("Done storing embeddings")
    db.get_stats()    

if __name__ == "__main__":
    store_embeddings()
