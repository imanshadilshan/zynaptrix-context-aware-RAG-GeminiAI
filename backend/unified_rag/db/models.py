from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float
from sqlalchemy.types import TypeDecorator, Text as SQLText
from unified_rag.db.database import Base
import json

# Custom Type Decorator to support both PostgreSQL pgvector and SQLite Text fallbacks
class SafeVector(TypeDecorator):
    impl = SQLText
    cache_ok = True

    def __init__(self, dim=768, *args, **kwargs):
        self.dim = dim
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(self.dim))
            except ImportError:
                print("WARNING: pgvector package is not installed but postgres dialect is used. Falling back to Text.")
                return dialect.type_descriptor(SQLText())
        else:
            return dialect.type_descriptor(SQLText())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        # In SQLite, save the list/ndarray as a JSON string
        if isinstance(value, str):
            return value
        return json.dumps(list(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        # In SQLite, parse the JSON string back into a list of floats
        try:
            return json.loads(value)
        except Exception:
            return value

class ManualChunk(Base):
    __tablename__ = "manual_chunks"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    manual_id = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False) # 'text', 'image', 'table'
    content = Column(Text, nullable=True) # Text content or structured table string
    embedding = Column(SafeVector(768), nullable=False) # Dimension 768 for text-embedding-004
    page = Column(Integer, nullable=True)
    path = Column(String, nullable=True) # Path to the extracted image file

class Machine(Base):
    __tablename__ = "machines"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    manual_id = Column(String, nullable=False) # Maps to ManualChunk.manual_id

class InteractionMemory(Base):
    """
    Vectorized 'Historical Knowledge' derived from resolved incidents.
    This allows the RAG engine to prioritize previous successful fixes.
    """
    __tablename__ = "interaction_memory"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, index=True, nullable=False)
    manual_id = Column(String, nullable=False) # Origin manual
    summary = Column(Text, nullable=False) # Actionable summary (steps performed)
    operator_fix = Column(Text, nullable=True) # Final operator input
    embedding = Column(SafeVector(768), nullable=False) # 768 Gemini
    timestamp = Column(String, nullable=False)

class AssistantSession(Base):
    __tablename__ = "assistant_sessions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, index=True, nullable=True) # Context machine
    title = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

class AssistantMessage(Base):
    __tablename__ = "assistant_messages"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("assistant_sessions.id"), nullable=False)
    role = Column(String, nullable=False) # 'agent' | 'user'
    content = Column(Text, nullable=False)
    type = Column(String, default='text') # 'text', 'wizard_step', etc.
    step_data = Column(Text, nullable=True) # JSON string
    images = Column(Text, nullable=True) # JSON list of URLs for agent responses
    timestamp = Column(String, nullable=False)

class Manual(Base):
    """Stores metadata for source PDF manuals stored in Cloudinary."""
    __tablename__ = "manuals"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    manual_id = Column(String, unique=True, index=True, nullable=False)
    filename = Column(String, nullable=False)
    url = Column(String, nullable=False) # Cloudinary URL or local path
    created_at = Column(String, nullable=True)
