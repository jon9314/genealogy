from fastapi import APIRouter, UploadFile, File, Depends
from sqlmodel import Session

from ..db import get_session
from ..core.gedcom import import_gedcom

router = APIRouter(prefix="/import", tags=["import"])

@router.post("/gedcom")
async def import_gedcom_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    content = await file.read()
    gedcom_data = content.decode("utf-8")
    
    # TODO: Implement actual merging logic and rollback
    imported_data = import_gedcom(session, gedcom_data)
    
    return {"message": "GEDCOM file imported successfully", "data": imported_data}
