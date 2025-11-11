from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..core.gedcom import import_gedcom
from ..core.models import Source, Person, Family, Child

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/gedcom")
async def import_gedcom_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """Import GEDCOM file and merge with existing database.

    Returns import statistics and any errors encountered.
    """
    try:
        content = await file.read()
        gedcom_data = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    try:
        imported_data = import_gedcom(session, gedcom_data)

        message = "GEDCOM file imported successfully"
        if imported_data.get("errors"):
            message += f" with {len(imported_data['errors'])} warnings"

        return {"message": message, "data": imported_data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.delete("/rollback/{source_id}")
async def rollback_import(
    source_id: int,
    session: Session = Depends(get_session)
):
    """Rollback (undo) a GEDCOM import by deleting all records from that source.

    This allows users to undo an import they're not happy with.
    """
    try:
        # Verify the source exists and is an import
        source = session.exec(select(Source).where(Source.id == source_id)).first()
        if not source:
            raise HTTPException(status_code=404, detail="Import source not found")

        if not source.name.startswith("GEDCOM Import"):
            raise HTTPException(
                status_code=400,
                detail="Can only rollback GEDCOM imports, not OCR sources"
            )

        # Delete all children from families linked to this source
        families_to_delete = session.exec(
            select(Family).where(Family.source_id == source_id)
        ).all()

        for family in families_to_delete:
            children = session.exec(
                select(Child).where(Child.family_id == family.id)
            ).all()
            for child in children:
                session.delete(child)

        # Delete all families from this source
        for family in families_to_delete:
            session.delete(family)

        # Delete all persons from this source
        persons_to_delete = session.exec(
            select(Person).where(Person.source_id == source_id)
        ).all()

        deleted_counts = {
            "persons": len(persons_to_delete),
            "families": len(families_to_delete)
        }

        for person in persons_to_delete:
            session.delete(person)

        # Delete the source itself
        session.delete(source)
        session.commit()

        return {
            "message": "Import rolled back successfully",
            "deleted": deleted_counts
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")
