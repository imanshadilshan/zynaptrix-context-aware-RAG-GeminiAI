from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
import shutil
import os
from datetime import datetime

from unified_rag.ingestion.pipeline import process_manual_async
from unified_rag.db.database import get_db
from unified_rag.db.models import Manual
from services.cloudinary_service import CloudinaryService

router = APIRouter(prefix="/api/rag", tags=["Manual Ingestion"])

@router.post("/ingest-manual")
async def ingest_manual(
    manual_id: str = Form(...),
    file: UploadFile = File(...)
):
    print(f"\n🚀 [API] Received ingestion request for Manual ID: {manual_id}")
    print(f"📄 [API] File: {file.filename}")

    if not file.filename.endswith(".pdf"):
        print(f"❌ [API] Rejected: {file.filename} is not a PDF")
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{manual_id}_{file.filename}")
    
    print(f"💾 [API] Saving file to: {file_path}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Cloud Sync (Source PDF)
    url = None
    try:
        cloud = CloudinaryService()
        if cloud.enabled:
            print(f"☁️ [API] Uploading source PDF for {manual_id} to Cloudinary...")
            url = cloud.upload_file(
                file_path, 
                public_id=f"manual_{manual_id}", 
                folder="industrial_copilot/data/manuals",
                resource_type="raw"
            )
    except Exception as e:
        print(f"⚠️ [API] Source PDF cloud sync failed: {e}")

    # Register/Update Manual Record in DB
    db = next(get_db())
    try:
        manual_record = db.query(Manual).filter(Manual.manual_id == manual_id).first()
        if not manual_record:
            manual_record = Manual(manual_id=manual_id)
            db.add(manual_record)
        manual_record.filename = file.filename
        manual_record.url = url or file_path
        manual_record.created_at = datetime.now().isoformat()
        db.commit()
        print(f"✅ [API] Manual {manual_id} registered successfully.")
    except Exception as e:
        print(f"❌ [API] DB registration failed for Manual: {e}")
        db.rollback()
    finally:
        db.close()

    print(f"✅ [API] File saved. Starting ingestion pipeline...")
        
    # Process immediately
    try:
        result = await process_manual_async(file_path, manual_id)
        print(f"🏁 [API] Ingestion successful for {manual_id}!")
        return {"message": "Manual ingested successfully", "details": result}
    except Exception as e:
        print(f"🔥 [API] CRITICAL ERROR during ingestion: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@router.get("/manuals")
async def list_manuals(db: Session = Depends(get_db)):
    """List all technical manuals successfully registered/uploaded in the platform."""
    return db.query(Manual).all()
