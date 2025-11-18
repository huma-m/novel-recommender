from typing import Dict, List
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, Mapped, mapped_column
from datetime import datetime, timezone
import json
import pandas as pd

Base = declarative_base()

class Novel(Base):
    __tablename__ = 'novels'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    link = Column(String(500), unique=True, nullable=False)
    description = Column(Text)
    genres = Column(JSON)
    tags = Column(JSON)
    last_update = Column(DateTime, default=datetime.now(timezone.utc))
    
    # tag_embedding: Mapped[list[float]]= mapped_column(JSON)
    # desc_embedding: Mapped[list[float]]= mapped_column(JSON)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            "description": self.description,
            "genres": self.genres,
            "tags": self.tags
        }

class NovelDB:
    def __init__(self, db_path: str = "data/novels_db.db"):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def add_novel(self, novel_data: Dict):
        session = self.Session()
        try:
            existing = session.query(Novel).filter_by(link=novel_data['link']).first()
            if existing:
                return "exists"
            novel = Novel(
                title = novel_data['title'],
                link = novel_data["link"],
                description = novel_data.get("description", ""),
                genres = novel_data.get("genres", []),
                tags = novel_data.get("tags", []),
            )
            session.add(novel)
            session.commit()
            return "added"
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
        
    def get_novel_by_link(self, link: str):
        session = self.Session()
        try:
            novel = session.query(Novel).filter_by(link=link).first()
            return novel.to_dict() if novel else None
        finally:
            session.close()
    
    def get_novel_by_title(self, title: str):
        session = self.Session()
        try:
            novel = session.query(Novel).filter_by(title=title).first()
            return novel.to_dict() if novel else None
        finally:
            session.close()
    
    def search_novels_by_title(self, query: str, limit: int = 10):
        session = self.Session()
        try:
            novels = session.query(Novel).filter(Novel.title.contains(query)).limit(limit).all()
            return [novel.to_dict() for novel in novels]
        finally:
            session.close()
            
    def get_all_novels(self):
        with self.Session() as session:
            novels = session.query(Novel).all()
            data = [novel.to_dict() for novel in novels]
            return pd.DataFrame(data)            
            
    def export_to_json(self, json_path: str):
        session = self.Session()
        try:
            novels = session.query(Novel).all()
            novels_list = [novel.to_dict() for novel in novels]
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(novels_list, f, ensure_ascii=False, indent=2)
        finally:
            session.close()
            
    def get_novel_count(self) -> int:
        session = self.Session()
        try:
            return session.query(Novel).count()
        finally:
            session.close()
        
    # def store_embeddings(self, id: int, tag_embedding: List[float], desc_embedding: List[float]):
    #     session = self.Session()
    #     try:
    #         novel = session.query(Novel).filter_by(id=id).first()
    #         if novel:
    #             novel.tag_embedding = tag_embedding
    #             novel.desc_embedding = desc_embedding
    #             session.commit()
    #     except Exception as e:
    #         session.rollback()
    #         raise e
    #     finally:
    #         session.close()
            
    # def get_embeddings(self, id: int):
    #     session = self.Session()
    #     try:
    #         novel = session.query(Novel).filter_by(id=id).first()
    #         if novel: 
    #             tag_emb = novel.tag_embedding if novel.tag_embedding else None
    #             desc_emb = novel.desc_embedding if novel.desc_embedding else None
    #             return tag_emb, desc_emb
    #         return None, None
    #     finally:
    #         session.close()
            
def migrate_from_json(json_path: str, db_path: str = "data/novels_db.db"):
    novel_db = NovelDB(db_path)
    with open(json_path, 'r', encoding='utf-8') as f:
        novels_data = json.load(f)
        for novel_data in novels_data:
            novel_db.add_novel(novel_data)
        return novel_db
            
# if __name__ == "__main__":
#     db = migrate_from_json("data/processed/novel_details_cleaned.json")
#     df = db.get_all_novels()
#     print(f"Total novels in DB: {db.get_novel_count()}")
#     pd.set_option('display.max_columns', None)
#     print(df.dtypes)
#     print(df.head())