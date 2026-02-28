import json
import os
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()
DATABASE_URL = "sqlite:///veritasguard.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class KnownHoax(Base):
    __tablename__ = "known_hoaxes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim = Column(String(500), nullable=False)
    verdict = Column(String(50), nullable=False)
    explanation = Column(Text, nullable=False)
    languages = Column(Text, default="[]")
    keywords = Column(Text, default="[]")


def init_db():
    Base.metadata.create_all(bind=engine)


def seed_hoaxes():
    session = SessionLocal()
    try:
        if session.query(KnownHoax).count() > 0:
            return

        data_path = os.path.join(os.path.dirname(__file__), "data", "known_hoaxes.json")
        with open(data_path, "r", encoding="utf-8") as f:
            hoaxes = json.load(f)

        for hoax in hoaxes:
            entry = KnownHoax(
                claim=hoax["claim"],
                verdict=hoax["verdict"],
                explanation=hoax["explanation"],
                languages=json.dumps(hoax.get("languages", [])),
                keywords=json.dumps(hoax.get("keywords", []))
            )
            session.add(entry)
        session.commit()
    finally:
        session.close()


def search_hoaxes(text: str) -> list[dict]:
    session = SessionLocal()
    try:
        results = []
        all_hoaxes = session.query(KnownHoax).all()
        text_lower = text.lower()

        for hoax in all_hoaxes:
            keywords = json.loads(hoax.keywords)
            matches = sum(1 for kw in keywords if kw.lower() in text_lower)
            if matches >= 2:
                results.append({
                    "claim": hoax.claim,
                    "verdict": hoax.verdict,
                    "explanation": hoax.explanation,
                    "match_score": matches / len(keywords) if keywords else 0
                })

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results
    finally:
        session.close()
