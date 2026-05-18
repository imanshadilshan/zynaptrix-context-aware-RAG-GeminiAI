from unified_rag.config import settings
from unified_rag.gemini_client import get_client

MODEL = "gemini-2.5-flash"

class TableTransformer:
    def __init__(self):
        self.api_key = settings.gemini_api_key

    def summarize_table(self, table_json: str, context: str = "") -> str:
        """
        Uses Gemini to transform raw technical table JSON into a dense, searchable summary.
        """
        if not self.api_key:
            print("⚠️ [TableTransformer] Gemini API key not set. Skipping table summarization.")
            return f"Table Data: {table_json[:500]}..."

        prompt = (
            "You are a Technical Data Specialist. Convert this raw table JSON into a concise, searchable summary.\n"
            f"Context: {context}\n"
            "Format your response as a clear description. Focus on key specifications, ranges, and part numbers.\n"
            "Include every unique column name and its meaning in the context of the technical manual.\n"
            "If it's a troubleshooting table, list the Problem-Cause-Solution pairs in a dense format."
        )

        try:
            response = get_client().models.generate_content(
                model=MODEL,
                contents=f"{prompt}\n\nRAW TABLE DATA:\n{table_json}"
            )
            return response.text.strip()
        except Exception as e:
            print(f"❌ [TableTransformer] Error summarizing table with Gemini: {e}")
            return f"Table Data: {table_json[:500]}..."
