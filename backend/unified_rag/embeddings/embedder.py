import google.generativeai as genai
from unified_rag.config import settings

class MultimodalEmbedder:
    def __init__(self):
        # Configure the Google Generative AI client
        api_key = settings.gemini_api_key
        if not api_key:
            print("WARNING: GEMINI_API_KEY is not set.")
        else:
            genai.configure(api_key=api_key)
        self.text_model = "models/text-embedding-004" # 768 dimensions by default
        
    def embed_text(self, text: str, task_type: str = "retrieval_document") -> list[float]:
        """Embeds text, tables, and vision-generated image captions using Gemini."""
        api_key = settings.gemini_api_key
        if not api_key:
            raise ValueError("Gemini API key not configured. Check your environment.")
        
        # Ensure client is configured
        genai.configure(api_key=api_key)
        
        try:
            response = genai.embed_content(
                model=self.text_model,
                content=text,
                task_type=task_type
            )
            return response['embedding']
        except Exception as e:
            print(f"❌ [Embedder] Gemini embedding call failed: {e}")
            raise e

embedder = MultimodalEmbedder()
