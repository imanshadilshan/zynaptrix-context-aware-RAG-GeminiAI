import google.generativeai as genai
from unified_rag.config import settings

class SafetyCriticAgent:
    """
    Safety Auditor Agent: Audits procedural maintenance steps and reviews
    them to guarantee that safety parameters (PPE, Lockout/Tagout - LOTO)
    are placed prominently at the very top of instructions.
    """
    def __init__(self):
        self.api_key = settings.gemini_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def audit_response(self, text: str) -> str:
        """
        Reviews and audits the RAG/Assistant response.
        If it contains actionable instructions or repair procedures:
         1. Ensures Lockout/Tagout (LOTO) is enforced.
         2. Ensures proper PPE is listed.
         3. Prepends a Safety Seal of Approval.
        """
        if not self.api_key:
            return text

        # Check if the text actually has steps/procedures. If not, no safety audit is needed
        lower_text = text.lower()
        has_steps = any(kw in lower_text for kw in ["step ", "phase", "procedure", "repair", "fix", "1.", "loto"])
        
        if not has_steps:
            return text

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = (
            "You are a Senior Safety & Compliance Engineer for heavy machinery operations.\n\n"
            "YOUR JOB:\n"
            "Audit the generated maintenance guide text. If it describes any physical actions or repairs, "
            "make sure it features clear Lockout/Tagout (LOTO) and Personal Protective Equipment (PPE) instructions "
            "AT THE ABSOLUTE TOP of the task list.\n\n"
            "RULES:\n"
            "1. If LOTO/PPE instructions are already present, do not modify them, but prepend a clean safety approval banner.\n"
            "2. If they are missing or vague, gently edit the beginning of the steps to explicitly insert clear, structured LOTO (e.g. isolate energy source, apply lock) and PPE requirements.\n"
            "3. Keep the original technical steps completely intact. Do not lose any surrounding text or figure references.\n"
            "4. Format the safety warnings in a distinct markdown blockquote with a '🛡️ **SAFETY COMPLIANCE APPROVED**' header.\n\n"
            "INPUT TEXT TO AUDIT:\n"
            f"{text}"
        )

        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"❌ [SafetyCriticAgent] Audit failed: {e}")
            return f"🛡️ **SAFETY MANDATE (PPE & LOTO Enforced)**\n*Technician: Ensure Lockout/Tagout protocol is verified and appropriate PPE (gloves, goggles) is equipped before starting.*\n\n{text}"
