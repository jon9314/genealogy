from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import or_
from sqlmodel import Session, select

from ..core.models import Child, Family, Person, PersonRead, PersonUpdate
from ..db import get_session

router = APIRouter(prefix="/persons", tags=["persons"])


class BulkUpdateRequest(BaseModel):
    person_ids: List[int]
    updates: dict  # Fields to update (sex, surname, etc.)


class BulkDeleteRequest(BaseModel):
    person_ids: List[int]
    keep_person_id: Optional[int] = None  # If provided, keeps this person and deletes others


@router.get("", response_model=List[PersonRead])
def list_persons(
    source_id: Optional[int] = None,
    gen: Optional[int] = None,
    q: Optional[str] = None,
    session: Session = Depends(get_session),
) -> List[PersonRead]:
    statement = select(Person)
    if source_id is not None:
        statement = statement.where(Person.source_id == source_id)
    if gen is not None:
        statement = statement.where(Person.gen == gen)
    if q:
        statement = statement.where(func.lower(Person.name).contains(q.lower()))
    statement = statement.order_by(Person.gen, Person.id)
    people = session.exec(statement).all()
    return list(people)


@router.patch("/{person_id}", response_model=PersonRead)
def update_person(person_id: int, payload: PersonUpdate, session: Session = Depends(get_session)) -> PersonRead:
    person = session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(person, field, value)
    session.add(person)
    session.commit()
    session.refresh(person)
    return person


@router.delete("/{person_id}")
def delete_person(person_id: int, session: Session = Depends(get_session)) -> JSONResponse:
    person = session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    children = session.exec(select(Child).where(Child.person_id == person_id)).all()
    for child in children:
        session.delete(child)

    families = session.exec(
        select(Family).where(or_(Family.husband_id == person_id, Family.wife_id == person_id))
    ).all()
    for family in families:
        if family.husband_id == person_id:
            family.husband_id = None
        if family.wife_id == person_id:
            family.wife_id = None
        session.add(family)

    session.delete(person)
    session.commit()
    return JSONResponse({"status": "deleted"})


@router.post("/bulk-update")
def bulk_update_persons(
    request: BulkUpdateRequest,
    session: Session = Depends(get_session)
) -> JSONResponse:
    """
    Bulk update multiple persons with the same field values.
    Useful for setting sex on all people with a specific name.
    """
    if not request.person_ids:
        raise HTTPException(status_code=400, detail="No person IDs provided")

    updated_count = 0
    for person_id in request.person_ids:
        person = session.get(Person, person_id)
        if not person:
            continue

        for field, value in request.updates.items():
            if hasattr(person, field):
                setattr(person, field, value)

        session.add(person)
        updated_count += 1

    session.commit()
    return JSONResponse({
        "status": "updated",
        "count": updated_count,
        "person_ids": request.person_ids
    })


@router.post("/bulk-delete")
def bulk_delete_persons(
    request: BulkDeleteRequest,
    session: Session = Depends(get_session)
) -> JSONResponse:
    """
    Bulk delete multiple persons (e.g., duplicates).
    Optionally specify one person to keep and delete all others.
    """
    if not request.person_ids:
        raise HTTPException(status_code=400, detail="No person IDs provided")

    person_ids_to_delete = request.person_ids
    if request.keep_person_id:
        person_ids_to_delete = [pid for pid in request.person_ids if pid != request.keep_person_id]

    deleted_count = 0
    for person_id in person_ids_to_delete:
        person = session.get(Person, person_id)
        if not person:
            continue

        # Delete child relationships
        children = session.exec(select(Child).where(Child.person_id == person_id)).all()
        for child in children:
            session.delete(child)

        # Update family relationships
        families = session.exec(
            select(Family).where(or_(Family.husband_id == person_id, Family.wife_id == person_id))
        ).all()
        for family in families:
            if family.husband_id == person_id:
                family.husband_id = None
            if family.wife_id == person_id:
                family.wife_id = None
            session.add(family)

        session.delete(person)
        deleted_count += 1

    session.commit()
    return JSONResponse({
        "status": "deleted",
        "count": deleted_count,
        "deleted_ids": person_ids_to_delete,
        "kept_id": request.keep_person_id
    })
