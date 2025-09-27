from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlmodel import Session, select

from ..core.models import Child, Family, Person, PersonRead, PersonUpdate
from ..db import get_session

router = APIRouter(prefix="/persons", tags=["persons"])


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
