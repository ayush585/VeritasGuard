import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.database import (
    Base,
    KnownHoax,
    VerificationRecord,
    create_db_engine,
    get_database_url,
    seed_hoaxes,
)


def _ensure_source_exists(source_url: str) -> bool:
    if not source_url.startswith("sqlite:///"):
        return True
    db_path = source_url.replace("sqlite:///", "", 1)
    return Path(db_path).exists()


def main() -> int:
    load_dotenv()

    source_url = os.getenv("SOURCE_SQLITE_URL", "sqlite:///veritasguard.db")
    target_url = get_database_url()

    if not target_url:
        print("DATABASE_URL is required for migration.")
        return 1

    if source_url == target_url:
        print("Source and target databases are identical. Migration aborted.")
        return 1

    if not _ensure_source_exists(source_url):
        print(f"Source database does not exist: {source_url}")
        return 1

    source_engine = create_db_engine(source_url)
    target_engine = create_db_engine(target_url)
    SourceSession = sessionmaker(bind=source_engine, autoflush=False, autocommit=False)
    TargetSession = sessionmaker(bind=target_engine, autoflush=False, autocommit=False)

    Base.metadata.create_all(bind=target_engine)

    source = SourceSession()
    target = TargetSession()
    migrated_hoaxes = 0
    migrated_records = 0
    try:
        existing_hoaxes = {row.claim: row for row in target.query(KnownHoax).all()}
        for row in source.query(KnownHoax).all():
            if row.claim in existing_hoaxes:
                existing = existing_hoaxes[row.claim]
                existing.verdict = row.verdict
                existing.explanation = row.explanation
                existing.languages = row.languages
                existing.keywords = row.keywords
            else:
                target.add(
                    KnownHoax(
                        claim=row.claim,
                        verdict=row.verdict,
                        explanation=row.explanation,
                        languages=row.languages,
                        keywords=row.keywords,
                    )
                )
            migrated_hoaxes += 1

        existing_results = {
            row.verification_id: row for row in target.query(VerificationRecord).all()
        }
        for row in source.query(VerificationRecord).all():
            if row.verification_id in existing_results:
                existing = existing_results[row.verification_id]
                existing.status = row.status
                existing.payload = row.payload
                existing.created_at = row.created_at
                existing.updated_at = row.updated_at
            else:
                target.add(
                    VerificationRecord(
                        verification_id=row.verification_id,
                        status=row.status,
                        payload=row.payload,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
                )
            migrated_records += 1

        target.commit()
        print(
            f"Migrated known_hoaxes={migrated_hoaxes}, verification_results={migrated_records} "
            f"from {source_url} to {target_url}"
        )
    finally:
        source.close()
        target.close()

    seed_hoaxes()
    print("Reseeded known hoaxes from server/data/known_hoaxes.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
