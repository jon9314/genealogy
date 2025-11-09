"""API endpoints for data validation."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from ..core.models import Child, Family, Person
from ..core.validator import validate_all_data
from ..db import get_session

router = APIRouter(prefix="/validation", tags=["validation"])


@router.get("/warnings")
def get_validation_warnings(session: Session = Depends(get_session)) -> List[dict]:
    """
    Run all data validation checks and return warnings.

    Returns warnings for:
    - Impossible dates (death before birth, child born before parent)
    - Suspicious age gaps (spouses with >25 year gap, parent <12 or >60 at child's birth)
    - Duplicate names within families
    - Unrealistic lifespans (>120 years)
    """
    warnings = validate_all_data(session)
    return warnings


@router.get("/relationships")
def validate_relationships(session: Session = Depends(get_session)) -> JSONResponse:
    """
    Validate relationship data and detect orphans.
    Returns orphans and suspicious relationship patterns.
    """
    issues: List[dict] = []

    # Get all people
    all_people = session.exec(select(Person)).all()
    person_map = {p.id: p for p in all_people if p.id is not None}

    # Get all families
    all_families = session.exec(select(Family)).all()

    # Track people who have family connections
    connected_person_ids = set()

    # Check family relationships
    for family in all_families:
        if family.husband_id:
            connected_person_ids.add(family.husband_id)
        if family.wife_id:
            connected_person_ids.add(family.wife_id)

        # Check for missing spouse
        if family.husband_id and not family.wife_id:
            husband = person_map.get(family.husband_id)
            if husband:
                issues.append({
                    "type": "missing_spouse",
                    "severity": "info",
                    "message": f"{husband.name} has a family but no spouse recorded",
                    "person_ids": [family.husband_id],
                    "family_id": family.id
                })
        elif family.wife_id and not family.husband_id:
            wife = person_map.get(family.wife_id)
            if wife:
                issues.append({
                    "type": "missing_spouse",
                    "severity": "info",
                    "message": f"{wife.name} has a family but no spouse recorded",
                    "person_ids": [family.wife_id],
                    "family_id": family.id
                })

    # Get all children
    all_children = session.exec(select(Child)).all()
    for child_link in all_children:
        connected_person_ids.add(child_link.person_id)

    # Detect orphans (people with no family connections)
    orphans = []
    for person_id, person in person_map.items():
        if person_id not in connected_person_ids:
            orphans.append({
                "id": person.id,
                "name": person.name,
                "gen": person.gen,
                "birth": person.birth,
                "death": person.death,
                "surname": person.surname
            })

    return JSONResponse({
        "orphans": orphans,
        "orphan_count": len(orphans),
        "total_people": len(all_people),
        "connected_people": len(connected_person_ids),
        "issues": issues,
        "issue_count": len(issues)
    })
