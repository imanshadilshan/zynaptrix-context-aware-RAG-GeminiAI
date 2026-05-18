from google.genai import types
from unified_rag.config import settings
from unified_rag.gemini_client import get_client

class MultimodalEmbedder:
    def __init__(self):
        self.text_model = "text-embedding-004"

    def embed_text(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        if not settings.gemini_api_key:
            raise ValueError("Gemini API key not configured. Check your environment.")
        try:
            result = get_client().models.embed_content(
                model=self.text_model,
                contents=text,
                config=types.EmbedContentConfig(task_type=task_type)
            )
            return result.embeddings[0].values
        except Exception as e:
            print(f"❌ [Embedder] Gemini embedding call failed: {e}")
            raise e

embedder = MultimodalEmbedder()
