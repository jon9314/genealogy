from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_
from sqlmodel import Session, select

from ..core.models import (
    Child,
    ChildRead,
    Family,
    FamilyRead,
    FamilyUpdate,
    FamilyWithChildren,
    Person,
    ReparentRequest,
)
from ..db import get_session

router = APIRouter(prefix="/families", tags=["families"])


@router.get("", response_model=List[FamilyWithChildren])
def list_families(session: Session = Depends(get_session)) -> List[FamilyWithChildren]:
    families = session.exec(select(Family)).all()
    children = session.exec(select(Child)).all()
    children_by_family: dict[int, list[ChildRead]] = {}
    for child in children:
        children_by_family.setdefault(child.family_id, []).append(ChildRead.from_orm(child))
    for items in children_by_family.values():
        items.sort(key=lambda item: item.order_index)

    response: List[FamilyWithChildren] = []
    for family in families:
        payload = FamilyWithChildren.from_orm(family)
        payload.children = children_by_family.get(family.id or 0, [])
        response.append(payload)
    return response


@router.patch("/{family_id}", response_model=FamilyRead)
def update_family(family_id: int, payload: FamilyUpdate, session: Session = Depends(get_session)) -> FamilyRead:
    family = session.get(Family, family_id)
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(family, field, value)
    session.add(family)
    session.commit()
    session.refresh(family)
    return family


@router.post("/reparent")
def reparent_child(payload: ReparentRequest, session: Session = Depends(get_session)) -> JSONResponse:
    person = session.get(Person, payload.person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    existing_links = session.exec(select(Child).where(Child.person_id == person.id)).all()
    for link in existing_links:
        session.delete(link)

    target_family_id: int | None = payload.new_family_id
    if target_family_id is None:
        if payload.new_parent_person_id is None:
            raise HTTPException(status_code=400, detail="Must provide new_family_id or new_parent_person_id")
        parent = session.get(Person, payload.new_parent_person_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent person not found")
        if parent.id == person.id:
            raise HTTPException(status_code=400, detail="Cannot set a person as their own parent")
        family = session.exec(
            select(Family).where(or_(Family.husband_id == parent.id, Family.wife_id == parent.id))
        ).first()
        if family is None:
            family = Family()
            if parent.sex == "F":
                family.wife_id = parent.id
            else:
                family.husband_id = parent.id
            session.add(family)
            session.flush()
        target_family_id = family.id
    else:
        family = session.get(Family, target_family_id)
        if not family:
            raise HTTPException(status_code=404, detail="Target family not found")

    max_index = session.exec(
        select(func.max(Child.order_index)).where(Child.family_id == target_family_id)
    ).one()[0]
    next_index = (max_index or 0) + 1
    new_child = Child(family_id=target_family_id, person_id=person.id, order_index=next_index)
    session.add(new_child)
    session.commit()
    return JSONResponse({"status": "ok", "family_id": target_family_id})
