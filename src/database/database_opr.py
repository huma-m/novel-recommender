from typing import Dict, List
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, ForeignKey, select
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Mapped, mapped_column
from datetime import datetime, timezone
import json
from pathlib import Path
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
    last_update: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    
    tag_embedding: Mapped[list[float]]= mapped_column(JSON)
    desc_embedding: Mapped[list[float]]= mapped_column(JSON)
    
    recommendations = relationship(
        'Recommendation', 
        foreign_keys="[Recommendation.novel_id]",
        back_populates='source', 
        cascade="all, delete-orphan",
    )
    recommendate_by = relationship(
        'Recommendation', 
        foreign_keys="[Recommendation.recommendation_id]",
        back_populates="target",
    )
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            "description": self.description,
            "genres": self.genres,
            "tags": self.tags,
            "tag_embedding": self.tag_embedding,
            "desc_embedding": self.desc_embedding
        }

class Recommendation(Base):
    __tablename__ = 'recommendations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False)
    recommendation_id = Column(Integer, ForeignKey("novels.id"), nullable=False)
    
    source = relationship(
        "Novel",
        foreign_keys=[novel_id],
        back_populates="recommendations",
    )
    target = relationship(
        "Novel",
        foreign_keys=[recommendation_id],
        back_populates="recommendate_by",
    )
    
class NovelDB:
    def __init__(self, db_path: str = "data/novels_db.db"):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
       
    def add_novels(self, df):
        session = self.Session()
        try:
            records = df.to_dict("records")  
            links = [r["link"] for r in records]

            existing = session.query(Novel).filter(Novel.link.in_(links)).all()
            existing_map = {nov.link: nov for nov in existing}

            new_objects = []

            for row in records:
                link = row["link"]

                if link in existing_map:
                    nov = existing_map[link]
                    nov.description = row.get("description", nov.description)
                    nov.genres = row.get("genres", nov.genres)
                    nov.tags = row.get("tags", nov.tags)
                    nov.last_update = datetime.now(timezone.utc)
                else:
                    new_objects.append(
                        Novel(
                            title=row["title"],
                            link=row["link"],
                            description=row.get("description", ""),
                            genres=row.get("genres", []),
                            tags=row.get("tags", []),
                        )
                    )

            if new_objects:
                session.add_all(new_objects)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            
    def add_novel(self, novel_data: Dict):
        session = self.Session()
        try:
            exist = session.query(Novel).filter_by(link=novel_data['link']).first()
            if exist:
                exist.description = novel_data.get('description', exist.description)
                exist.genres = novel_data.get('genres', exist.genres)
                exist.tags = novel_data.get('tags', exist.tags)
                exist.last_update = datetime.now(timezone.utc)
                novel_id = exist.id
            else:
                novel = Novel(
                    title = novel_data['title'],
                    link = novel_data["link"],
                    description = novel_data.get("description", ""),
                    genres = novel_data.get("genres", []),
                    tags = novel_data.get("tags", []),
                )
                session.add(novel)
                session.flush()
                novel_id = novel.id
                
            session.commit()
            return novel_id
        except Exception as e:
            session.rollback()
            raise 
        finally:
            session.close()
    
    def add_recommendations(self, novel_id, recommendations: List[Dict], scrape_json_path: str = "data/to_be_scraped.json"):
        session = self.Session()
        to_scrape = []
        try:
            existing_links = {
                link: id_ for id_, link in session.query(Novel.id, Novel.link).all()
            }
            new_novels = []
            recs = []
            
            for rec in recommendations:
                link = rec["link"]
                if link in existing_links:
                    rec_id = existing_links[link]
                else:
                    new_novels.append(
                        Novel(
                            title=rec.get("title"),
                            link=rec["link"],
                            description="",
                            genres=[],
                            tags=[],
                        )
                    )
                    
            if new_novels:
                session.add_all(new_novels)
                session.flush()
                for n in new_novels:
                    to_scrape.append({
                        "title": n.title,
                        "link": n.link
                    })
                    existing_links[n.link] = n.id
                    
            for rec in recommendations:
                rec_id = existing_links[rec["link"]]
                exists = session.query(Recommendation).filter_by(
                    novel_id=novel_id, recommendation_id=rec_id
                ).first()
                
                if not exists:
                    recs.append(Recommendation(novel_id=novel_id, recommendation_id=rec_id))
            
            if recs:
                session.add_all(recs)
            session.commit()
                
            if to_scrape:
                path = Path(scrape_json_path)
                if path.exists():
                    existing = json.loads(path.read_text(encoding='utf-8',errors="replace"))
                else:
                    existing = []
                    
                existing_ids = {item['link'] for item in existing}
                to_scrape = [item for item in to_scrape if item['link'] not in existing_ids]
                if to_scrape:
                    existing.extend(to_scrape)
                    path.write_text(json.dumps(existing, indent=2), encoding='utf-8')
                
        except Exception:
            session.rollback()
            raise 
        finally:
            session.close()
                    
    def get_recommedations(self, novel_id: int):
        session = self.Session()
        try:
            query = (
                select(Novel)
                .join(Recommendation, Recommendation.recommendation_id == Novel.id)
                .where(Recommendation.novel_id == novel_id)) 
            novels = session.execute(query).scalars().all()
            return novels
        except Exception as e:
            raise e
        finally:
            session.close()
    
    def get_ids_from_links(self, links):
        session = self.Session()
        try:
            rows = (
                session.query(Novel.id, Novel.link)
                .filter(Novel.link.in_(links))
                .all()
            )
            return {link: id_ for id_, link in rows}
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
            return session.query(Novel).all()            
            
    def get_completed_novels(self):
        session = self.Session()
        try:
            completed_novels = session.query(Novel).filter(
                    Novel.description != "",
                    Novel.tags.isnot(None), Novel.tags != [],
                    Novel.genres.isnot(None), Novel.genres != []
                ).all()
            df = pd.DataFrame([n.to_dict() for n in completed_novels])
            return df
        finally:
            session.close()
            
    def get_missing_embedding(self):
        session = self.Session()
        try:
            return session.query(Novel).filter(
                    Novel.description != "",
                    Novel.tags.isnot(None), Novel.tags != [],
                    Novel.genres.isnot(None), Novel.genres != [],
                    Novel.tag_embedding.is_(None),
                    Novel.desc_embedding.is_(None)
                ).all()
        finally:
            session.close()
            
    def export_to_json(self, json_path: str):
        session = self.Session()
        try:
            novels = session.query(Novel).all()
            novels_list = [novel.to_dict() for novel in novels]
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(novels_list, f, ensure_ascii=False, indent=2)
        finally:
            session.close()
            
    def get_stats(self):
        session = self.Session()
        try:
            total_novels = session.query(Novel).count()
            
            completed_details = session.query(Novel).filter(
                Novel.description != "",
                Novel.tags.isnot(None), Novel.tags != [],
                Novel.genres.isnot(None), Novel.genres != []
            ).count()

            # Novels with tag embedding
            with_tag_embedding = session.query(Novel).filter(
                Novel.tag_embedding.isnot(None)
            ).count()

            # Novels with desc embedding
            with_desc_embedding = session.query(Novel).filter(
                Novel.desc_embedding.isnot(None)
            ).count()

            # Novels that have at least one recommendation
            novels_with_recs = session.query(
                Recommendation.novel_id
            ).distinct().count()

            print(f"""
            total_novels: {total_novels},
            completed_details: {completed_details},
            with_tag_embedding: {with_tag_embedding},
            with_desc_embedding: {with_desc_embedding},
            novels_with_recommendations: {novels_with_recs}
            """)
        finally:
            session.close()
        
    def store_embeddings(self, df):
        session = self.Session()
        try: 
            ids = df['id'].tolist()
            
            novels = (
                session.query(Novel)
                .filter(Novel.id.in_(ids))
                .all()
            )
            novel_map = {nov.id: nov for nov in novels}

            for row in df.to_dict("records"):
                novel_id = row.get('id')
                novel = novel_map.get(novel_id)
                
                if not novel:
                    print(f"novel not found id: {novel_id}")
                    continue
                
                tag_emb = row.get('tag_embedding')
                desc_emb = row.get('desc_embedding')
                
                if tag_emb is not None:
                    if isinstance(tag_emb, (list, tuple)):
                        novel.tag_embedding = list(tag_emb)
                    else:
                        print(f"Invalid tag_embedding format for novel id: {novel_id}")
            
                if desc_emb is not None:
                    if isinstance(desc_emb, (list, tuple)):
                        novel.desc_embedding = list(desc_emb)
                    else:
                        print(f"Invalid desc_embedding format for novel id: {novel_id}")
            session.commit()
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            
    def get_embeddings(self, id: int):
        session = self.Session()
        try:
            novel = session.query(Novel).filter_by(id=id).first()
            if novel: 
                tag_emb = novel.tag_embedding if novel.tag_embedding else None
                desc_emb = novel.desc_embedding if novel.desc_embedding else None
                return tag_emb, desc_emb
            return None, None
        finally:
            session.close()
            
def migrate_from_json(json_path: str, db_path: str = "data/novels_db.db"):
    novel_db = NovelDB(db_path)
    with open(json_path, 'r', encoding='utf-8') as f:
        novels_data = json.load(f)
        for novel_data in novels_data:
            novel_db.add_novel(novel_data)
        return novel_db
            
if __name__ == "__main__":
    # db = migrate_from_json("data/processed/novel_details_cleaned.json")
    db = NovelDB()
    db.get_stats()
    # df = db.get_all_novels()
    # print(f"Total novels in DB: {db.get_novel_count()}")
    # pd.set_option('display.max_columns', None)
    # print(df.dtypes)
    # print(df.head())