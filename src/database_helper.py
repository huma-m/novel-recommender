from typing import Dict, List
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Mapped, mapped_column, aliased
from datetime import datetime, timezone
import pandas as pd
import os

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
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.getenv("DB_PATH", "data/novels_demo.db")
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
    
    def add_recommendations(self, novel_id, recommendations: List[Dict]):
        session = self.Session()
        try:
            req_links = {rec["link"] for rec in recommendations}
            existing_novels = session.query(Novel.id, Novel.link).filter(
                Novel.link.in_(req_links)
            ).all()
        
            link_to_id = {link: id_ for id_, link in existing_novels}
        
            new_novels = []
            
            for rec in recommendations:
                if rec["link"] not in link_to_id:
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
                for novel in new_novels:
                    link_to_id[novel.link] = novel.id
                    
            target_rec_ids = list(link_to_id.values())
            existing_recs = session.query(Recommendation.recommendation_id).filter(
                Recommendation.novel_id == novel_id,
                Recommendation.recommendation_id.in_(target_rec_ids)
            ).all()
        
            already_linked_ids = {r[0] for r in existing_recs}
            recs_to_add = []
            for rec_id in target_rec_ids:
                if rec_id not in already_linked_ids:
                    recs_to_add.append(
                        Recommendation(novel_id=novel_id, recommendation_id=rec_id)
                    )
            
            if recs_to_add:
                session.add_all(recs_to_add)
            session.commit()    
        except Exception:
            session.rollback()
            raise 
        finally:
            session.close()
   
    def get_skeleton_novels(self, limit=100):
        session = self.Session()
        try:
            return (
                session.query(Novel)
                .filter(
                    (Novel.description == "") |
                    (Novel.tags == []) |
                    (Novel.genres == [])
                )
                .limit(limit)
                .all()
            )
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
                    Novel.genres.isnot(None), Novel.genres != [],
                    # TEMPORARY
                    Novel.tag_embedding.isnot(None),
                    Novel.desc_embedding.isnot(None)
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

    def get_recommendation_pairs(self):
        session = self.Session()
        try:
            Source = aliased(Novel)
            Target = aliased(Novel)

            query = (
                session.query(
                    Recommendation.novel_id,
                    Recommendation.recommendation_id
                )
                .join(Source, Recommendation.novel_id == Source.id)
                .join(Target, Recommendation.recommendation_id == Target.id)
                .filter(
                    Source.description.isnot(None), Source.description != "",
                    Source.tags.isnot(None), Source.tags != [],

                    Target.description.isnot(None), Target.description != "",
                    Target.tags.isnot(None), Target.tags != [],
                )
            )
            return query.all()

        finally:
            session.close()
