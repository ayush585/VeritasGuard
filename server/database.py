import json
import os
import re
import unicodedata
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()
DATABASE_URL = "sqlite:///veritasguard.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
HOAX_REFERENCE_MAP: dict[str, list[dict]] = {}


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
    global HOAX_REFERENCE_MAP
    session = SessionLocal()
    try:
        data_path = os.path.join(os.path.dirname(__file__), "data", "known_hoaxes.json")
        with open(data_path, "r", encoding="utf-8-sig") as f:
            hoaxes = json.load(f)
        HOAX_REFERENCE_MAP = {h.get("claim", ""): h.get("references", []) for h in hoaxes if h.get("claim")}

        existing = {entry.claim: entry for entry in session.query(KnownHoax).all()}
        for hoax in hoaxes:
            if hoax["claim"] in existing:
                entry = existing[hoax["claim"]]
                entry.verdict = hoax["verdict"]
                entry.explanation = hoax["explanation"]
                entry.languages = json.dumps(hoax.get("languages", []))
                entry.keywords = json.dumps(hoax.get("keywords", []))
            else:
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
    def normalize(value: str) -> str:
        normalized = unicodedata.normalize("NFKC", str(value or "")).lower()
        normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
        return re.sub(r"\s+", " ", normalized).strip()

    def tokenize(value: str) -> set[str]:
        return set(normalize(value).split())

    session = SessionLocal()
    try:
        results = []
        all_hoaxes = session.query(KnownHoax).all()
        text_normalized = normalize(text)
        text_tokens = tokenize(text)

        for hoax in all_hoaxes:
            keywords = json.loads(hoax.keywords)
            languages = json.loads(hoax.languages) if hoax.languages else []
            keyword_hits = 0
            token_overlap_hits = 0
            exact_claim_match = normalize(hoax.claim) in text_normalized if hoax.claim else False
            for kw in keywords:
                kw_norm = normalize(kw)
                if not kw_norm:
                    continue
                if kw_norm in text_normalized:
                    keyword_hits += 1
                    continue
                kw_tokens = tokenize(kw_norm)
                if kw_tokens and len(text_tokens.intersection(kw_tokens)) >= max(1, len(kw_tokens) // 2):
                    token_overlap_hits += 1

            matches = keyword_hits + token_overlap_hits
            if matches >= 2 or (keyword_hits >= 1 and token_overlap_hits >= 1):
                score = min(
                    1.0,
                    (0.28 * keyword_hits)
                    + (0.22 * token_overlap_hits)
                    + (0.35 if exact_claim_match else 0.0),
                )
                results.append({
                    "claim": hoax.claim,
                    "verdict": hoax.verdict,
                    "explanation": hoax.explanation,
                    "match_score": round(score, 3),
                    "keyword_hits": keyword_hits,
                    "token_overlap_hits": token_overlap_hits,
                    "exact_claim_match": exact_claim_match,
                    "keywords": keywords,
                    "languages": languages,
                    "references": HOAX_REFERENCE_MAP.get(hoax.claim, []),
                })

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results
    finally:
        session.close()
