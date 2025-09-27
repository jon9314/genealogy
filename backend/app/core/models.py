from __future__ import annotations

from datetime import datetime
from typing import Optional

import re

from sqlalchemy import UniqueConstraint, and_, or_
from sqlmodel import Field, Session, SQLModel, select


class SourceBase(SQLModel):
    name: str
    path: str
    pages: int = 0
    ocr_done: bool = False


class Source(SourceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class SourceCreate(SourceBase):
    pass


class SourceRead(SourceBase):
    id: int


class PageTextBase(SQLModel):
    source_id: int = Field(foreign_key="source.id")
    page_index: int
    text: str


class PageText(PageTextBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class PageTextRead(PageTextBase):
    id: int


class PersonBase(SQLModel):
    chart_id: Optional[str] = None
    gen: int
    name: str
    given: Optional[str] = None
    surname: Optional[str] = None
    birth: Optional[str] = None
    death: Optional[str] = None
    sex: Optional[str] = Field(default=None, regex="^[MF]$")
    title: Optional[str] = None
    notes: Optional[str] = None
    source_id: Optional[int] = Field(default=None, foreign_key="source.id")
    page_index: Optional[int] = None
    line_index: Optional[int] = None


class Person(PersonBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    line_key: Optional[str] = Field(default=None, index=True)
    normalized_given: Optional[str] = Field(default=None, index=True)
    normalized_surname: Optional[str] = Field(default=None, index=True)
    birth_year: Optional[int] = Field(default=None, index=True)

    __table_args__ = (
        UniqueConstraint("source_id", "line_key", name="uq_person_source_line"),
    )

    @classmethod
    def _normalize_name(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        token = value.lower()
        token = "".join(ch for ch in token if ch.isalpha())
        return token or None

    @classmethod
    def _extract_year(cls, value: Optional[str]) -> Optional[int]:
        if not value:
            return None
        match = re.search(r"(\d{4})", value)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    @classmethod
    def _levenshtein(cls, a: Optional[str], b: Optional[str]) -> int:
        if a is None or b is None:
            return 999
        if a == b:
            return 0
        la, lb = len(a), len(b)
        if la == 0:
            return lb
        if lb == 0:
            return la
        prev = list(range(lb + 1))
        for i, ca in enumerate(a, start=1):
            curr = [i]
            for j, cb in enumerate(b, start=1):
                cost = 0 if ca == cb else 1
                curr.append(
                    min(
                        curr[j - 1] + 1,
                        prev[j] + 1,
                        prev[j - 1] + cost,
                    )
                )
            prev = curr
        return prev[-1]

    @classmethod
    def upsert_from_parse(
        cls,
        session: Session,
        source_id: int,
        given: Optional[str],
        surname: Optional[str],
        vitals: Optional[dict] = None,
        line_key: Optional[str] = None,
    ) -> "Person":
        normalized_given = cls._normalize_name(given)
        normalized_surname = cls._normalize_name(surname)

        birth_value = None
        death_value = None
        birth_year = None
        if vitals:
            birth_value = vitals.get("birth") if isinstance(vitals, dict) else None
            death_value = vitals.get("death") if isinstance(vitals, dict) else None
            if isinstance(birth_value, dict):
                birth_year = birth_value.get("year") or cls._extract_year(birth_value.get("raw"))
                birth_value = birth_value.get("raw") or birth_value.get("text")
            elif isinstance(birth_value, str):
                birth_year = cls._extract_year(birth_value)
            if isinstance(death_value, dict):
                death_value = death_value.get("raw") or death_value.get("text")

        query = select(cls).where(cls.source_id == source_id)
        person: Optional[Person] = None
        if line_key:
            person = session.exec(query.where(cls.line_key == line_key)).first()

        if person is None and normalized_surname:
            candidates = session.exec(
                query.where(cls.normalized_surname == normalized_surname)
            ).all()
            for candidate in candidates:
                if birth_year is not None and candidate.birth_year not in (None, birth_year):
                    continue
                distance = cls._levenshtein(normalized_given, candidate.normalized_given)
                if distance <= 2:
                    person = candidate
                    break

        created = False
        if person is None:
            person = cls(
                source_id=source_id,
                given=given,
                surname=surname,
                birth=birth_value if isinstance(birth_value, str) else birth_value,
                death=death_value if isinstance(death_value, str) else death_value,
                line_key=line_key,
                normalized_given=normalized_given,
                normalized_surname=normalized_surname,
                birth_year=birth_year,
            )
            session.add(person)
            session.flush()
            created = True
        else:
            updated = False

            def merge(attr: str, value: Optional[str]) -> None:
                nonlocal updated
                if value and not getattr(person, attr):
                    setattr(person, attr, value)
                    updated = True

            merge("given", given)
            merge("surname", surname)
            merge("birth", birth_value if isinstance(birth_value, str) else birth_value)
            merge("death", death_value if isinstance(death_value, str) else death_value)

            if line_key and not person.line_key:
                person.line_key = line_key
                updated = True
            if normalized_given and person.normalized_given != normalized_given:
                person.normalized_given = normalized_given
                updated = True
            if normalized_surname and person.normalized_surname != normalized_surname:
                person.normalized_surname = normalized_surname
                updated = True
            if birth_year and person.birth_year != birth_year:
                person.birth_year = birth_year
                updated = True
            if updated:
                session.add(person)

        return person


class PersonRead(PersonBase):
    id: int


class PersonUpdate(SQLModel):
    name: Optional[str] = None
    given: Optional[str] = None
    surname: Optional[str] = None
    birth: Optional[str] = None
    death: Optional[str] = None
    sex: Optional[str] = Field(default=None, regex="^[MF]$")
    title: Optional[str] = None
    notes: Optional[str] = None
    chart_id: Optional[str] = None


class FamilyBase(SQLModel):
    husband_id: Optional[int] = Field(default=None, foreign_key="person.id")
    wife_id: Optional[int] = Field(default=None, foreign_key="person.id")
    notes: Optional[str] = None


class Family(FamilyBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: Optional[int] = Field(default=None, foreign_key="source.id", index=True)
    is_single_parent: bool = Field(default=False, index=True)

    __table_args__ = (
        UniqueConstraint("source_id", "husband_id", "wife_id", name="uq_family_couple"),
    )

    @classmethod
    def upsert_couple(
        cls,
        session: Session,
        source_id: int,
        person_a_id: int,
        person_b_id: int,
    ) -> "Family":
        if person_a_id == person_b_id:
            return cls.ensure_for_single_parent(session, source_id, person_a_id)

        pair = sorted((person_a_id, person_b_id))
        existing = session.exec(
            select(cls).where(
                and_(
                    cls.source_id == source_id,
                    or_(
                        and_(cls.husband_id == pair[0], cls.wife_id == pair[1]),
                        and_(cls.husband_id == pair[1], cls.wife_id == pair[0]),
                    ),
                )
            )
        ).first()
        if existing:
            if existing.husband_id not in pair or existing.wife_id not in pair:
                existing.husband_id, existing.wife_id = pair
                session.add(existing)
            existing.is_single_parent = False
            return existing

        family = cls(
            source_id=source_id,
            husband_id=pair[0],
            wife_id=pair[1],
            is_single_parent=False,
        )
        session.add(family)
        session.flush()
        return family

    @classmethod
    def ensure_for_single_parent(
        cls,
        session: Session,
        source_id: int,
        parent_id: int,
    ) -> "Family":
        existing = session.exec(
            select(cls).where(
                and_(
                    cls.source_id == source_id,
                    cls.is_single_parent.is_(True),
                    or_(cls.husband_id == parent_id, cls.wife_id == parent_id),
                )
            )
        ).first()
        if existing:
            return existing

        parent = session.get(Person, parent_id)
        husband_id = parent_id if not parent or parent.sex != "F" else None
        wife_id = parent_id if parent and parent.sex == "F" else None

        family = cls(
            source_id=source_id,
            husband_id=husband_id,
            wife_id=wife_id,
            is_single_parent=True,
        )
        session.add(family)
        session.flush()
        return family


class FamilyRead(FamilyBase):
    id: int


class FamilyUpdate(SQLModel):
    husband_id: Optional[int] = None
    wife_id: Optional[int] = None
    notes: Optional[str] = None


class ChildBase(SQLModel):
    family_id: int = Field(foreign_key="family.id")
    person_id: int = Field(foreign_key="person.id")
    order_index: int = 0


class Child(ChildBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    __table_args__ = (
        UniqueConstraint("family_id", "person_id", name="uq_child_membership"),
    )

    @classmethod
    def link(cls, session: Session, family_id: int, child_id: int) -> "Child":
        existing = session.exec(
            select(cls).where(
                and_(cls.family_id == family_id, cls.person_id == child_id)
            )
        ).first()
        if existing:
            return existing

        order_query = session.exec(
            select(cls).where(cls.family_id == family_id).order_by(cls.order_index.desc())
        ).first()
        order_index = (order_query.order_index + 1) if order_query else 0
        child = cls(family_id=family_id, person_id=child_id, order_index=order_index)
        session.add(child)
        session.flush()
        return child


class ChildRead(ChildBase):
    id: int


class FamilyWithChildren(FamilyRead):
    children: list[ChildRead] = Field(default_factory=list)


class ReparentRequest(SQLModel):
    person_id: int
    new_family_id: Optional[int]
    new_parent_person_id: Optional[int]


class ProjectPayload(SQLModel):
    exported_at: datetime
    sources: list[Source]
    pages: list[PageText]
    persons: list[Person]
    families: list[Family]
    children: list[Child]
