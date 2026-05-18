from sqlalchemy.orm import Session
from unified_rag.db.models import ManualChunk, InteractionMemory
from unified_rag.embeddings.embedder import embedder
import numpy as np
import json

def cosine_similarity(v1, v2):
    if v1 is None or v2 is None:
        return 0.0
    # SQLite fallback might store vector as a JSON string, let's load it if necessary
    if isinstance(v1, str):
        v1 = json.loads(v1)
    if isinstance(v2, str):
        v2 = json.loads(v2)
        
    vec1 = np.array(v1, dtype=float)
    vec2 = np.array(v2, dtype=float)
    
    dot_product = np.dot(vec1, vec2)
    norm_v1 = np.linalg.norm(vec1)
    norm_v2 = np.linalg.norm(vec2)
    
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

class RetrievalEngine:
    def __init__(self, top_k_text=3, top_k_image=3, top_k_memory=2):
        self.top_k_text = top_k_text
        self.top_k_image = top_k_image
        self.top_k_memory = top_k_memory
        
    def retrieve(self, db: Session, query: str, manual_id: str, machine_id: str = None):
        """
        Dual-Source Vector Search:
        1. Manual Documentation (Theoretical Knowledge)
        2. Interaction Memory (Historical Field Fixes)
        """
        # 1. Embed query
        query_emb = embedder.embed_text(query, task_type="retrieval_query")
        
        is_sqlite = db.bind.dialect.name == "sqlite"
        
        # 2. Search Manual Text/Tables
        if is_sqlite:
            try:
                all_text_chunks = db.query(ManualChunk).filter(
                    ManualChunk.manual_id == manual_id,
                    ManualChunk.type.in_(["text", "table"])
                ).all()
                
                scored_chunks = []
                for c in all_text_chunks:
                    score = cosine_similarity(c.embedding, query_emb)
                    scored_chunks.append((c, score))
                
                # Sort descending by score
                scored_chunks.sort(key=lambda x: x[1], reverse=True)
                text_results = [item[0] for item in scored_chunks[:self.top_k_text]]
            except Exception as e:
                print(f"Error doing in-memory SQLite text retrieval: {e}")
                text_results = []
        else:
            try:
                text_results = db.query(ManualChunk).filter(
                    ManualChunk.manual_id == manual_id,
                    ManualChunk.type.in_(["text", "table"])
                ).order_by(
                    ManualChunk.embedding.cosine_distance(query_emb)
                ).limit(self.top_k_text).all()
            except Exception as e:
                print(f"Error doing PG text retrieval: {e}")
                text_results = []
            
        # 3. Search Manual Images/Figures
        if is_sqlite:
            try:
                all_image_chunks = db.query(ManualChunk).filter(
                    ManualChunk.manual_id == manual_id,
                    ManualChunk.type == "image"
                ).all()
                
                scored_images = []
                for c in all_image_chunks:
                    score = cosine_similarity(c.embedding, query_emb)
                    scored_images.append((c, score))
                
                scored_images.sort(key=lambda x: x[1], reverse=True)
                raw_image_results = [item[0] for item in scored_images[:self.top_k_image * 2]]
            except Exception as e:
                print(f"Error doing SQLite image retrieval: {e}")
                raw_image_results = []
        else:
            try:
                raw_image_results = db.query(ManualChunk).filter(
                    ManualChunk.manual_id == manual_id,
                    ManualChunk.type == "image"
                ).order_by(
                    ManualChunk.embedding.cosine_distance(query_emb)
                ).limit(self.top_k_image * 2).all()
            except Exception as e:
                print(f"Error doing PG image retrieval: {e}")
                raw_image_results = []

        # Deduplicate images by path
        image_results = []
        seen_paths = set()
        for img in raw_image_results:
            if img.path not in seen_paths:
                seen_paths.add(img.path)
                image_results.append(img)
            if len(image_results) >= self.top_k_image:
                break

        # 4. Search Interaction Memory (History)
        historical_fixes = []
        if machine_id:
            if is_sqlite:
                try:
                    all_fixes = db.query(InteractionMemory).filter(
                        InteractionMemory.machine_id == machine_id
                    ).all()
                    
                    scored_fixes = []
                    for f in all_fixes:
                        score = cosine_similarity(f.embedding, query_emb)
                        scored_fixes.append((f, score))
                    
                    scored_fixes.sort(key=lambda x: x[1], reverse=True)
                    historical_fixes = [item[0] for item in scored_fixes[:self.top_k_memory]]
                except Exception as e:
                    print(f"Error retrieving in-memory SQLite history: {e}")
            else:
                try:
                    historical_fixes = db.query(InteractionMemory).filter(
                        InteractionMemory.machine_id == machine_id
                    ).order_by(
                        InteractionMemory.embedding.cosine_distance(query_emb)
                    ).limit(self.top_k_memory).all()
                except Exception as e:
                    print(f"Error retrieving PG history: {e}")
            
        return {
            "text_chunks": text_results,
            "images": image_results,
            "historical_fixes": historical_fixes
        }
