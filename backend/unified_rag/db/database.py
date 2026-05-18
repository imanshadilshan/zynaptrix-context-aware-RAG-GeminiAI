from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from unified_rag.config import settings
import os

db_url = settings.database_url

if not db_url:
    # Local development SQLite fallback
    os.makedirs("data", exist_ok=True)
    db_url = "sqlite:///data/rag.db"
    print(f"⚠️ DATABASE_URL is not set. Falling back to local SQLite database: {db_url}")
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}
    )
else:
    print(f"🔌 Connecting to PostgreSQL database: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    engine = create_engine(
        db_url,
        pool_pre_ping=True,  # Check connection health before using it
        pool_recycle=3600    # Prevent stale connections by recycling hourly
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
