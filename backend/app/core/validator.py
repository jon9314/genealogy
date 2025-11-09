"""Data validation module for genealogy records.

Checks for data quality issues like impossible dates, suspicious age gaps,
and duplicate names within families.
"""

from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session, select

from .models import Child, Family, Person


class ValidationWarning:
    """Represents a data quality warning."""

    def __init__(
        self,
        severity: str,  # "error", "warning", "info"
        category: str,  # "dates", "age_gaps", "duplicates"
        message: str,
        person_ids: List[int],
        family_id: Optional[int] = None,
    ):
        self.severity = severity
        self.category = category
        self.message = message
        self.person_ids = person_ids
        self.family_id = family_id

    def to_dict(self):
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "person_ids": self.person_ids,
            "family_id": self.family_id,
        }


def extract_year(date_str: Optional[str]) -> Optional[int]:
    """Extract year from date string."""
    if not date_str:
        return None
    import re
    match = re.search(r'\d{4}', date_str)
    return int(match.group()) if match else None


def validate_person_dates(person: Person) -> List[ValidationWarning]:
    """Check for impossible dates within a single person record."""
    warnings = []

    birth_year = extract_year(person.birth)
    death_year = extract_year(person.death)

    # Death before birth
    if birth_year and death_year and death_year < birth_year:
        warnings.append(ValidationWarning(
            severity="error",
            category="dates",
            message=f"{person.name}: Death year ({death_year}) is before birth year ({birth_year})",
            person_ids=[person.id],
        ))

    # Unrealistic lifespan (over 120 years)
    if birth_year and death_year and (death_year - birth_year) > 120:
        warnings.append(ValidationWarning(
            severity="warning",
            category="dates",
            message=f"{person.name}: Lifespan of {death_year - birth_year} years seems unusually long",
            person_ids=[person.id],
        ))

    return warnings


def validate_parent_child_dates(
    parent: Person,
    child: Person,
    family_id: int
) -> List[ValidationWarning]:
    """Check for impossible parent-child date relationships."""
    warnings = []

    parent_birth = extract_year(parent.birth)
    child_birth = extract_year(child.birth)

    if not parent_birth or not child_birth:
        return warnings

    age_at_birth = child_birth - parent_birth

    # Child born before parent
    if age_at_birth < 0:
        warnings.append(ValidationWarning(
            severity="error",
            category="dates",
            message=f"{child.name} born before parent {parent.name} (parent birth: {parent_birth}, child birth: {child_birth})",
            person_ids=[parent.id, child.id],
            family_id=family_id,
        ))

    # Parent too young (under 12)
    elif age_at_birth < 12:
        warnings.append(ValidationWarning(
            severity="warning",
            category="dates",
            message=f"{parent.name} was only {age_at_birth} when {child.name} was born",
            person_ids=[parent.id, child.id],
            family_id=family_id,
        ))

    # Parent too old (over 60)
    elif age_at_birth > 60:
        warnings.append(ValidationWarning(
            severity="warning",
            category="dates",
            message=f"{parent.name} was {age_at_birth} when {child.name} was born (unusually old)",
            person_ids=[parent.id, child.id],
            family_id=family_id,
        ))

    return warnings


def validate_spouse_age_gap(
    person1: Person,
    person2: Person,
    family_id: int
) -> List[ValidationWarning]:
    """Check for suspiciously large age gaps between spouses."""
    warnings = []

    birth1 = extract_year(person1.birth)
    birth2 = extract_year(person2.birth)

    if not birth1 or not birth2:
        return warnings

    age_gap = abs(birth1 - birth2)

    # Large age gap (over 25 years)
    if age_gap > 25:
        warnings.append(ValidationWarning(
            severity="warning",
            category="age_gaps",
            message=f"Large age gap between spouses {person1.name} and {person2.name}: {age_gap} years",
            person_ids=[person1.id, person2.id],
            family_id=family_id,
        ))

    return warnings


def validate_duplicate_names_in_family(
    family_id: int,
    children: List[Person]
) -> List[ValidationWarning]:
    """Check for duplicate names among children in the same family."""
    warnings = []

    name_map = {}
    for child in children:
        # Create a normalized key from name
        key = child.name.strip().lower() if child.name else ""
        if not key:
            continue

        if key in name_map:
            # Found duplicate
            warnings.append(ValidationWarning(
                severity="info",
                category="duplicates",
                message=f"Duplicate name '{child.name}' in family (IDs: {name_map[key]}, {child.id})",
                person_ids=[name_map[key], child.id],
                family_id=family_id,
            ))
        else:
            name_map[key] = child.id

    return warnings


def validate_all_data(session: Session) -> List[dict]:
    """Run all validation checks and return warnings."""
    all_warnings = []

    # 1. Validate all person records for impossible dates
    persons = session.exec(select(Person)).all()
    for person in persons:
        all_warnings.extend(validate_person_dates(person))

    # 2. Validate family relationships
    families = session.exec(select(Family)).all()
    for family in families:
        # Get parents
        husband = session.get(Person, family.husband_id) if family.husband_id else None
        wife = session.get(Person, family.wife_id) if family.wife_id else None

        # Check spouse age gap
        if husband and wife:
            all_warnings.extend(validate_spouse_age_gap(husband, wife, family.id))

        # Get children
        child_records = session.exec(
            select(Child).where(Child.family_id == family.id)
        ).all()

        children = []
        for child_record in child_records:
            child = session.get(Person, child_record.person_id)
            if child:
                children.append(child)

                # Validate parent-child dates
                if husband:
                    all_warnings.extend(validate_parent_child_dates(husband, child, family.id))
                if wife:
                    all_warnings.extend(validate_parent_child_dates(wife, child, family.id))

        # Check for duplicate names in family
        if len(children) > 1:
            all_warnings.extend(validate_duplicate_names_in_family(family.id, children))

    return [w.to_dict() for w in all_warnings]
