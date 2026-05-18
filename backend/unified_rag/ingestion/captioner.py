import google.generativeai as genai
from PIL import Image
import requests
from io import BytesIO
import os
from unified_rag.config import settings

class ImageCaptioner:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def generate_caption(self, image_path: str, metadata: dict = None) -> str:
        """
        Uses Gemini-2.5-Flash Vision to describe the image with full document context.
        Accepts both local file paths and public HTTPS URLs (e.g. Cloudinary).
        """
        if not self.api_key:
            print("⚠️ [Vision] Gemini API key not set. Skipping caption generation.")
            return f"Technical diagram on Page {metadata.get('page', 'Unknown')}."
            
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        metadata = metadata or {}
        page = metadata.get("page", "Unknown")
        section = metadata.get("section", "Unknown Section")
        label = metadata.get("label", "Diagram")
        parent_ctx = metadata.get("parent_context", "")

        context_str = f"This image is a technical illustration labeled '{label}' on Page {page} of the manual."
        if section != "Unknown Section":
            context_str += f" It is located within the section: '{section}'."
        if parent_ctx:
            context_str += f" Context: {parent_ctx}."

        print(f"      📸 [Vision] Sending image to Gemini with context: {label} (Page {page})")

        prompt = (
            f"You are a Senior Industrial Systems Engineer. {context_str}\n\n"
            "INSTRUCTIONS:\n"
            "1. Describe this specific technical component in extremely high detail.\n"
            "2. Explain its function and relationship to the surrounding assembly mentioned in the context.\n"
            "3. Identify any labels, bolts, connectors, or part numbers visible.\n"
            "4. Use professional engineering terminology. This description will be used for RAG retrieval, "
            "so include keywords that a technician would use when troubleshooting this specific part."
        )

        try:
            # Load the image from URL or Local Path
            if image_path.startswith("http"):
                response = requests.get(image_path, timeout=15)
                img = Image.open(BytesIO(response.content))
            else:
                if not os.path.exists(image_path):
                    raise FileNotFoundError(f"Local image path not found: {image_path}")
                img = Image.open(image_path)

            response = model.generate_content([prompt, img])
            caption = response.text.strip()
            return f"### {label} (Context: {section})\n\n{caption}"
            
        except Exception as e:
            print(f"      ❌ [Vision] Gemini Vision Call FAILED for {image_path}: {e}")
            return f"Technical diagram '{label}' on Page {page}. Description unavailable due to parsing error."
