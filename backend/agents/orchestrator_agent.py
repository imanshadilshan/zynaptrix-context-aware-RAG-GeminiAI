import google.generativeai as genai
import json
from unified_rag.config import settings
from unified_rag.db.database import SessionLocal
from unified_rag.db.models import AssistantSession, AssistantMessage, Machine, InteractionMemory
from agents.knowledge_agent import KnowledgeAgent, RAGMode
from agents.safety_critic_agent import SafetyCriticAgent
from agents.report_writer_agent import ReportWriterAgent
import datetime
import typing_extensions as typing

class ClassificationSchema(typing.TypedDict):
    intent: str # "RAG", "GUIDE", "ONBOARDING", "CHAT", "REPORT"
    explanation: str

class OrchestratorAgent:
    """
    Master Coordinator Agent: Coordinates Intent Routing, RAG Retrievals,
    Safety Audits, and stateful database history loops.
    """
    def __init__(self):
        self.api_key = settings.gemini_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.knowledge_agent = KnowledgeAgent()
        self.safety_critic = SafetyCriticAgent()
        self.report_writer = ReportWriterAgent()

    def classify_intent(self, user_query: str, chat_history: str = "") -> str:
        """
        Uses Gemini to classify user query intent for optimal routing.
        """
        if not self.api_key:
            return "RAG"
            
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = (
            "You are a routing agent for an industrial AI assistant.\n"
            "Classify the following user query into one of these intents:\n"
            " - 'ONBOARDING': Hello, greetings, intro, system capabilities, 'what can you do'.\n"
            " - 'GUIDE': Requests for step-by-step guides, troubleshooting steps, repair procedures, or the Conversational Wizard.\n"
            " - 'REPORT': Requests to generate/export a maintenance summary, incident logs, or technical reports.\n"
            " - 'CHAT': Friendly casual chitchat unrelated to machine errors.\n"
            " - 'RAG': Technical questions about machine specifications, manuals, lookup values, or incidents.\n\n"
            f"CHAT HISTORY:\n{chat_history}\n\n"
            f"USER QUERY: '{user_query}'"
        )
        
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=ClassificationSchema,
                    temperature=0.0
                )
            )
            data = json.loads(response.text)
            return data.get("intent", "RAG")
        except Exception as e:
            print(f"⚠️ [Orchestrator] Intent classification failed: {e}. Defaulting to RAG.")
            return "RAG"

    def handle_message(self, session_id: int, user_query: str) -> dict:
        """
        Handles stateful dialog loops.
        Pipes queries, retrieves RAG content, audits safety, and writes to database.
        """
        db = SessionLocal()
        try:
            # 1. Fetch Session
            session = db.query(AssistantSession).filter(AssistantSession.id == session_id).first()
            if not session:
                return {"error": "Session not found"}

            # Resolve manual associated with the active machine context
            manual_id = "Zynaptrix_9000"
            if session.machine_id:
                machine = db.query(Machine).filter(Machine.machine_id == session.machine_id).first()
                if machine:
                    manual_id = machine.manual_id

            # 2. Reconstruct chat history context
            messages = db.query(AssistantMessage).filter(AssistantMessage.session_id == session_id).order_by(AssistantMessage.id.asc()).all()
            history_str = ""
            for m in messages:
                history_str += f"{m.role.upper()}: {m.content}\n"

            # 3. Save User Message
            user_msg = AssistantMessage(
                session_id=session_id,
                role="user",
                content=user_query,
                timestamp=datetime.datetime.now().isoformat()
            )
            db.add(user_msg)
            db.commit()

            # 4. Intent Classification
            intent = self.classify_intent(user_query, history_str)
            print(f"🤖 [Orchestrator] Classified query intent: {intent}")

            agent_response = ""
            wizard_step_data = None
            retrieved_images = []

            # 5. Route Inquiries
            if intent == "ONBOARDING":
                agent_response = (
                    "### 🛠️ Welcome to the Zynaptrix Industrial AI Copilot!\n"
                    "I am your context-aware technical assistant. Here is what I can do for you:\n"
                    "1. **Stateful Troubleshooting Wizard**: Ask me how to fix any issue, and I will guide you step-by-step.\n"
                    "2. **Multimodal Manual Search**: Retrieve detailed drawings, specifications, and schematics.\n"
                    "3. **Incident Log Memory**: I prioritize previous field fixes from similar incidents on your active machine.\n"
                    "4. **Technical Reports**: Ask me to write a technical resolution report at the end of your fix.\n\n"
                    "To get started, select an active machine and tell me the problem!"
                )
            elif intent == "CHAT":
                agent_response = (
                    "Hello! I am ready to assist. Please let me know if there are any technical manuals to query, "
                    "or if you have a machine repair issue to guide you through."
                )
            elif intent == "REPORT":
                # Compile Dialog transcript
                chat_transcript = history_str + f"USER: {user_query}\n"
                report_data = self.report_writer.write_report(chat_transcript, session.machine_id or "Unknown", manual_id)
                agent_response = (
                    f"### 📋 Technical Resolution Report Generated!\n"
                    f"I have successfully compiled a professional maintenance report for **{report_data.get('machine_id')}**.\n\n"
                    f"**Diagnosis**: {report_data.get('diagnosis')}\n"
                    f"**Root Cause**: {report_data.get('root_cause')}\n"
                    f"**Status**: `{report_data.get('status')}`\n\n"
                    "You can now download the official PDF report using the **Export Report** button above!"
                )
                wizard_step_data = json.dumps(report_data)
            else:
                # GUIDE or RAG
                rag_mode = RAGMode.SUMMARY if intent == "RAG" else RAGMode.CONVERSATIONAL_WIZARD
                
                # If conversational wizard, and chat history contains steps, let's keep it structured
                if "generate full step-by-step repair procedure" in user_query.lower() or "[conversational_wizard]" in user_query.lower():
                    rag_mode = RAGMode.CONVERSATIONAL_WIZARD

                rag_res = self.knowledge_agent.query(
                    query=user_query,
                    manual_id=manual_id,
                    machine_id=session.machine_id,
                    mode=rag_mode,
                    chat_history=history_str
                )
                
                raw_answer = rag_res["answer"]
                retrieved_images = rag_res["images"]

                # 6. Safety Audit (Audit steps, ensure LOTO/PPE)
                agent_response = self.safety_critic.audit_response(raw_answer)

            # 7. Commit Agent Response
            agent_msg = AssistantMessage(
                session_id=session_id,
                role="agent",
                content=agent_response,
                type="wizard_step" if wizard_step_data else "text",
                step_data=wizard_step_data,
                images=json.dumps(retrieved_images),
                timestamp=datetime.datetime.now().isoformat()
            )
            db.add(agent_msg)
            
            # Update Session timestamp
            session.updated_at = datetime.datetime.now().isoformat()
            db.commit()

            return {
                "id": agent_msg.id,
                "role": "agent",
                "content": agent_response,
                "type": agent_msg.type,
                "step_data": wizard_step_data,
                "images": retrieved_images,
                "timestamp": agent_msg.timestamp
            }

        except Exception as e:
            print(f"❌ [Orchestrator] Error processing message: {e}")
            db.rollback()
            return {"error": f"Failed to process query: {str(e)}"}
        finally:
            db.close()
