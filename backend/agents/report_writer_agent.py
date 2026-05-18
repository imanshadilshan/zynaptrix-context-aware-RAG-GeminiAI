import json
from unified_rag.config import settings
from unified_rag.gemini_client import get_client
from google.genai import types
import typing_extensions as typing

MODEL = "gemini-2.5-flash"

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

    def write_report(self, chat_transcript: str, machine_id: str = "Unknown", manual_id: str = "Unknown") -> dict:
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

        prompt = (
            "You are an expert technical documenter. Review the following chat transcript between a field technician "
            "and a diagnostic copilot. Extract a structured maintenance and resolution report in valid JSON.\n\n"
            f"MACHINE CONTEXT: {machine_id}\n"
            f"DOCUMENTATION SOURCE: {manual_id}\n\n"
            "CHAT DIALOG TRANSCRIPT:\n"
            f"{chat_transcript}"
        )

        try:
            response = get_client().models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ReportSchema,
                    temperature=0.0
                )
            )
            report_data = json.loads(response.text)

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
