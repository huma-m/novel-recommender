from src.database.database_helper import NovelDB
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
    return db.get_completed_novels()

def get_gt_map(ids):
    db = get_db()
    gt_map = {}
    valid_ids = set(ids)

    for src, tgt in db.get_recommendation_pairs():
        if src in valid_ids and tgt in valid_ids:
            gt_map.setdefault(src, []).append(tgt)

    return gt_map