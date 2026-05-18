import logging
import json
import os
import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
import google.generativeai as genai

from unified_rag.config import settings
from unified_rag.db.database import get_db
from unified_rag.db.models import AssistantSession, AssistantMessage, Machine, InteractionMemory
from agents.orchestrator_agent import OrchestratorAgent

router = APIRouter(prefix="/api/assistant", tags=["Central Assistant"])
logger = logging.getLogger(__name__)

# Initialize Orchestrator Agent
orchestrator = OrchestratorAgent()

# Models
class AssistantQuery(BaseModel):
    query: str
    session_id: Optional[int] = None
    machine_id: Optional[str] = None

class AssistantSessionResponse(BaseModel):
    id: int
    machine_id: Optional[str]
    title: str
    timestamp: str

class AssistantMessageView(BaseModel):
    role: str
    content: str
    type: str
    step_data: Optional[Dict]
    images: List[str]
    timestamp: str

class CreateSessionRequest(BaseModel):
    machine_id: Optional[str] = None
    title: Optional[str] = None

# Helper Functions
def generate_session_title(query: str) -> str:
    """Generate a 3-4 word title for a new session based on the first query using Gemini."""
    if not settings.gemini_api_key:
        return "New Assistant Inquiry"
    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        res = model.generate_content(
            f"Generate a very short title (maximum 4 words) for a chat that starts with this question: '{query}'. "
            "Provide ONLY the title as plain text. No quotes. No surrounding text."
        )
        return res.text.strip().strip('"')
    except Exception as e:
        logger.warning(f"Failed to generate title: {e}")
        return "New Assistant Inquiry"

# ───── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=List[AssistantSessionResponse])
async def get_assistant_sessions(db: Session = Depends(get_db)):
    sessions = db.query(AssistantSession).order_by(desc(AssistantSession.updated_at)).all()
    return [{
        "id": s.id,
        "machine_id": s.machine_id,
        "title": s.title,
        "timestamp": s.updated_at
    } for s in sessions]

@router.post("/sessions")
async def create_assistant_session(req: CreateSessionRequest, db: Session = Depends(get_db)):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = req.title or "New Assistant Inquiry"
    session = AssistantSession(
        machine_id=req.machine_id,
        title=title,
        created_at=now,
        updated_at=now
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "machine_id": session.machine_id,
        "title": session.title,
        "timestamp": session.updated_at
    }

@router.delete("/sessions/{session_id}")
async def delete_assistant_session(session_id: int, db: Session = Depends(get_db)):
    db.query(AssistantMessage).filter(AssistantMessage.session_id == session_id).delete()
    db.query(AssistantSession).filter(AssistantSession.id == session_id).delete()
    db.commit()
    return {"status": "success"}

@router.get("/sessions/{session_id}/history", response_model=List[AssistantMessageView])
async def get_session_history(session_id: int, db: Session = Depends(get_db)):
    messages = db.query(AssistantMessage).filter(AssistantMessage.session_id == session_id).order_by(AssistantMessage.timestamp).all()
    return [{
        "role": m.role,
        "content": m.content,
        "type": m.type,
        "step_data": json.loads(m.step_data) if m.step_data else None,
        "images": json.loads(m.images) if m.images else [],
        "timestamp": m.timestamp
    } for m in messages]

@router.get("/sessions/{session_id}/report")
async def generate_report(session_id: int, db: Session = Depends(get_db)):
    """Generate structured diagnostic report from session using ReportWriterAgent."""
    session = db.query(AssistantSession).filter(AssistantSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(AssistantMessage).filter(AssistantMessage.session_id == session_id).order_by(AssistantMessage.timestamp).all()
    if not messages:
        raise HTTPException(status_code=400, detail="No messages in session")
    
    conversation = []
    all_images = []
    for m in messages:
        conversation.append(f"{m.role.upper()}: {m.content}")
        if m.images:
            try:
                all_images.extend(json.loads(m.images))
            except:
                pass
    
    conversation_text = "\n\n".join(conversation)
    
    # 1. Resolve Manual ID from machine registry
    manual_id = "Zynaptrix_9000"
    if session.machine_id:
        machine_record = db.query(Machine).filter(Machine.machine_id == session.machine_id).first()
        if machine_record:
            manual_id = machine_record.manual_id

    # 2. Invoke ReportWriterAgent
    report_data = orchestrator.report_writer.write_report(conversation_text, session.machine_id or "Unknown", manual_id)

    return {
        "sessionId": session.id,
        "machineId": session.machine_id,
        "problemDescription": report_data.get("diagnosis", "N/A"),
        "diagnosis": report_data.get("root_cause", "N/A"),
        "solutionSteps": report_data.get("steps_taken", []),
        "images": [{"url": u, "caption": f"Ref {i+1}"} for i, u in enumerate(list(set(all_images)))],
        "timestamp": session.created_at
    }

@router.post("")
async def system_assistant(req: AssistantQuery, db: Session = Depends(get_db)):
    """Main stateful interaction endpoint for the Central Assistant, coordinated by OrchestratorAgent."""
    active_session_id = req.session_id
    active_machine_id = req.machine_id

    # Session Management
    if active_session_id:
        session = db.query(AssistantSession).filter(AssistantSession.id == active_session_id).first()
        if session:
            if req.machine_id:
                session.machine_id = req.machine_id
            active_machine_id = active_machine_id or session.machine_id
    else:
        new_session = AssistantSession(
            machine_id=active_machine_id,
            title=generate_session_title(req.query),
            created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        active_session_id = new_session.id
    
    # Delegate reasoning, retrievals, safety critic reviews to OrchestratorAgent
    result = orchestrator.handle_message(active_session_id, req.query)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    result["session_id"] = active_session_id
    result["context_source"] = f"Manual" if active_machine_id else "AI"
    
    return result
