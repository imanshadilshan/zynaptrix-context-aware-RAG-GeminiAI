import google.generativeai as genai
import json
from unified_rag.config import settings
import typing_extensions as typing

class ReportSchema(typing.TypedDict):
    machine_id: str
    manual_id: str
    technician_name: str
    incident_date: str
    diagnosis: str
    root_cause: str
    steps_taken: list[str]
    prevention_measures: list[str]
    status: str # "RESOLVED", "PENDING_PARTS", "ESCALATED"

class ReportWriterAgent:
    """
    Report Writer Agent: Evaluates technician chat history transcript
    and extracts a clean, structured JSON maintenance report.
    """
    def __init__(self):
        self.api_key = settings.gemini_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def write_report(self, chat_transcript: str, machine_id: str = "Unknown", manual_id: str = "Unknown") -> dict:
        """
        Parses dialogue transcript and outputs structured maintenance report JSON.
        """
        if not self.api_key:
            return {
                "machine_id": machine_id,
                "manual_id": manual_id,
                "technician_name": "Technician",
                "incident_date": "Current Session",
                "diagnosis": "Gemini API key not configured.",
                "root_cause": "N/A",
                "steps_taken": [],
                "prevention_measures": [],
                "status": "ESCALATED"
            }

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = (
            "You are an expert technical documenter. Review the following chat transcript between a field technician "
            "and a diagnostic copilot. Extract a structured maintenance and resolution report in valid JSON.\n\n"
            f"MACHINE CONTEXT: {machine_id}\n"
            f"DOCUMENTATION SOURCE: {manual_id}\n\n"
            "CHAT DIALOG TRANSCRIPT:\n"
            f"{chat_transcript}"
        )

        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=ReportSchema,
                    temperature=0.0
                )
            )
            report_data = json.loads(response.text)
            
            # Ensure identifiers are populated if missing in transcript extraction
            if report_data.get("machine_id") in ["", "Unknown", None]:
                report_data["machine_id"] = machine_id
            if report_data.get("manual_id") in ["", "Unknown", None]:
                report_data["manual_id"] = manual_id
                
            return report_data
        except Exception as e:
            print(f"❌ [ReportWriterAgent] Report compilation failed: {e}")
            return {
                "machine_id": machine_id,
                "manual_id": manual_id,
                "technician_name": "Technician",
                "incident_date": "Current Session",
                "diagnosis": f"Report generation failed: {str(e)}",
                "root_cause": "N/A",
                "steps_taken": [],
                "prevention_measures": [],
                "status": "ESCALATED"
            }
