import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from unified_rag.db.database import get_db
from unified_rag.db.models import Machine

router = APIRouter(prefix="/api/machines", tags=["Machine Registry"])
logger = logging.getLogger(__name__)

# Pydantic Schemas
class MachineBase(BaseModel):
    machine_id: str
    name: str
    location: str
    manual_id: str

class MachineResponse(MachineBase):
    class Config:
        from_attributes = True

class MachineCreate(MachineBase):
    pass

@router.get("", response_model=List[MachineResponse])
async def list_machines(db: Session = Depends(get_db)):
    """List all machines registered in the platform."""
    return db.query(Machine).all()

@router.get("/{machine_id}", response_model=MachineResponse)
async def get_machine(machine_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed metadata for a registered machine."""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return machine

@router.post("", response_model=MachineResponse)
async def register_machine(machine: MachineCreate, db: Session = Depends(get_db)):
    """Enroll a new machine or update its registration info."""
    existing = db.query(Machine).filter(Machine.machine_id == machine.machine_id).first()
    if existing:
        # Update existing record
        existing.name = machine.name
        existing.location = machine.location
        existing.manual_id = machine.manual_id
        db.commit()
        db.refresh(existing)
        return existing
        
    db_machine = Machine(
        machine_id=machine.machine_id,
        name=machine.name,
        location=machine.location,
        manual_id=machine.manual_id
    )
    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)
    return db_machine

@router.post("/delete/{machine_id}")
async def decommission_machine(machine_id: str, db: Session = Depends(get_db)):
    """Decommission a machine and delete its record from the platform."""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    db.delete(machine)
    db.commit()
    return {"status": "decommissioned", "machine_id": machine_id}
