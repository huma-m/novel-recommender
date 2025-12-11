import pandas as pd
# from sentence_transformers import SentenceTransformer
from src.database.database_opr import NovelDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_db = None
def get_db():
    global _db
    if _db is None:
        _db = NovelDB("data/novels_db.db")
    return _db

def load_data():
    logger.info("Loading data")
    db = get_db()
    novels = db.get_missing_embedding()
    if novels:
        logger.info("Calling store_embeddings()")
        store_embeddings(novels)
    return db.get_completed_novels()

def store_embeddings(novels):
    from sentence_transformers import SentenceTransformer
    
    logger.info("Getting tag model")
    tag_model = SentenceTransformer('all-MiniLM-L6-v2')
    tag_texts = [" ".join(n.tags) for n in novels]
    logger.info("calculating tag embedding")
    tag_embedding = tag_model.encode(tag_texts, normalize_embeddings=True, batch_size=64, show_progress_bar=True)
    
    logger.info("Getting desc model")
    desc_model = SentenceTransformer('all-mpnet-base-v2')
    descriptions = [n.description.lower() for n in novels]
    logger.info("calculating desc embedding")
    desc_embedding = desc_model.encode(descriptions, normalize_embeddings=True, batch_size=64, show_progress_bar=True)
    
    results_df = pd.DataFrame({
        'id': novels['id'],
        'tag_embedding': tag_embedding.tolist(),
        'desc_embedding': desc_embedding.tolist() 
    })
    db = get_db()
    logger.info("Going to database to store embeddings")
    db.store_embeddings(results_df)
    logger.info("Done storing embeddings")
    
def search_novels(query: str, limit: int = 10):
    db = get_db()
    return db.search_novels_by_title(query, limit)

def get_novel_by_title(title: str):
    db = get_db()
    return db.get_novel_by_title(title)