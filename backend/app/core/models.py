from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


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
