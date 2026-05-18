import logging
import os
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from unified_rag.config import settings
from unified_rag.db.database import engine, Base
from unified_rag.api.endpoints import router as rag_router
from app.machine_api import router as machine_router
from app.assistant_api import router as assistant_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize DB Tables
def init_db():
    logger.info("Initializing database...")
    is_sqlite = engine.url.drivername == "sqlite"
    if not is_sqlite:
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                logger.info("✅ PostgreSQL pgvector extension enabled.")
        except Exception as e:
            logger.warning(f"Could not initialize vector extension (might already exist or SQLite fallback): {e}")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created/verified successfully.")
            break
        except Exception as e:
            logger.error(f"⚠️ DB connection retry ({attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                logger.critical("❌ Could not connect to database after retries.")

init_db()

app = FastAPI(title="Context-Aware Multi-Agent Gemini RAG Backend")

# Setup Directories & Mount Static Assets
DATA_DIR = "data"
os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "extracted"), exist_ok=True)
app.mount("/static", StaticFiles(directory=DATA_DIR), name="static")
logger.info(f"✅ Local static assets directory mounted at /static pointing to: {DATA_DIR}")

# CORS Middleware (Explicit origins required when allow_credentials=True)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
if settings.frontend_url:
    origins.append(settings.frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Router Abstractions
app.include_router(rag_router)
app.include_router(machine_router)
app.include_router(assistant_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
