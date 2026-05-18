import google.generativeai as genai
from unified_rag.config import settings

class TableTransformer:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def summarize_table(self, table_json: str, context: str = "") -> str:
        """
        Uses Gemini to transform raw technical table JSON into a dense, searchable summary.
        """
        if not self.api_key:
            print("⚠️ [TableTransformer] Gemini API key not set. Skipping table summarization.")
            return f"Table Data: {table_json[:500]}..."

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = (
            "You are a Technical Data Specialist. Convert this raw table JSON into a concise, searchable summary.\n"
            f"Context: {context}\n"
            "Format your response as a clear description. Focus on key specifications, ranges, and part numbers.\n"
            "Include every unique column name and its meaning in the context of the technical manual.\n"
            "If it's a troubleshooting table, list the Problem-Cause-Solution pairs in a dense format."
        )
        
        try:
            response = model.generate_content(
                f"{prompt}\n\nRAW TABLE DATA:\n{table_json}"
            )
            summary = response.text.strip()
            return summary
        except Exception as e:
            print(f"❌ [TableTransformer] Error summarizing table with Gemini: {e}")
            return f"Table Data: {table_json[:500]}..."
