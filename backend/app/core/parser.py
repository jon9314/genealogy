﻿from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple

from sqlalchemy import text
from sqlmodel import Session

from .models import Child, Family, Person

LOGGER = logging.getLogger(__name__)

DASH_VARIANTS = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"
PERSON_PATTERN = re.compile(r"^\s*(\d+)--\s+(.*)$")
SPOUSE_PATTERN = re.compile(r"^\s*sp-\s+(.*)$", re.IGNORECASE)
HEADER_PATTERNS = [
    re.compile(r"^\s*Page\s+\d+\s*$", re.IGNORECASE),
    re.compile(
        r"^\s*(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\s*$",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*(Descendancy|Descendency|Descendants|Genealogy)\b.*$", re.IGNORECASE),
]
APPROX_WORD_RE = re.compile(r"\b(?:abt|about|approx|around|circa|ca\.?|c\.?|bef\.?|aft\.?|before|after)\b", re.IGNORECASE)


_PERSON_APPROX_COLUMN_CHECKED = False


def normalize_text(value: str) -> str:
    text_value = value
    for ch in DASH_VARIANTS:
        text_value = text_value.replace(ch, "-")
    text_value = re.sub(r"\s+", " ", text_value)
    return text_value.strip()


def _is_header(line: str) -> bool:
    return any(pattern.match(line) for pattern in HEADER_PATTERNS)


def _split_records(line: str) -> List[str]:
    pattern = re.compile(r"(\d+--|sp-)", re.IGNORECASE)
    matches = list(pattern.finditer(line))
    if not matches:
        return [line]
    segments: List[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(line)
        segment = line[start:end].strip()
        if segment:
            segments.append(segment)
    prefix = line[: matches[0].start()].strip()
    if prefix and segments:
        segments[0] = (prefix + " " + segments[0]).strip()
    return segments


def normalize_ocr_text(page: str) -> List[str]:
    text_value = page.replace("\r\n", "\n").replace("\r", "\n")
    text_value = re.sub(r"(\w)-\n(\w)", r"\1\2", text_value)
    for ch in DASH_VARIANTS:
        text_value = text_value.replace(ch, "-")
    text_value = re.sub(r"(?m)^(\s*sp)\s*[-~]\s*", r"\1- ", text_value, flags=re.IGNORECASE)
    text_value = re.sub(r"(?m)^(\s*\d+)\s*-+\s*", r"\1-- ", text_value)

    lines: List[str] = []
    buffer: Optional[str] = None

    for raw_line in text_value.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if _is_header(stripped):
            continue
        collapsed = re.sub(r"\s+", " ", stripped)
        segments = _split_records(collapsed)
        for segment in segments:
            record = segment
            if PERSON_PATTERN.match(record) or SPOUSE_PATTERN.match(record):
                if buffer is not None:
                    lines.append(buffer)
                buffer = record
            else:
                if buffer is None:
                    buffer = record
                else:
                    buffer += " " + record
    if buffer is not None:
        lines.append(buffer)
    return lines


def iter_lines(pages: List[str]) -> Iterator[Tuple[int, int, str]]:
    for page_index, page in enumerate(pages):
        normalized = normalize_ocr_text(page)
        for line_index, line in enumerate(normalized):
            yield page_index, line_index, line


def _ensure_person_approx_column(session: Session) -> None:
    global _PERSON_APPROX_COLUMN_CHECKED
    if _PERSON_APPROX_COLUMN_CHECKED:
        return
    try:
        columns = session.exec(text('PRAGMA table_info(person)')).all()
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.error("Failed to inspect person table for approx column: %s", exc)
        _PERSON_APPROX_COLUMN_CHECKED = True
        return
    has_column = any(row[1] == 'approx' for row in columns)
    if not has_column:
        try:
            session.exec(text('ALTER TABLE person ADD COLUMN approx BOOLEAN'))
            session.commit()
        except OperationalError:
            session.rollback()
            LOGGER.error("Unable to add person.approx column. Run migrations or reset the database.")
        except Exception as exc:  # pragma: no cover - defensive
            session.rollback()
            LOGGER.error(
                "Unexpected error while adding person.approx column: %s. Run migrations or reset the database.",
                exc,
            )
    _PERSON_APPROX_COLUMN_CHECKED = True


def _make_line_key(source_id: int, page_index: int, line_index: int, raw_line: str) -> str:
    payload = f"{source_id}:{page_index}:{line_index}:{raw_line.strip()}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _build_vital(value: Optional[str]) -> Optional[Dict[str, object]]:
    if not value:
        return None
    cleaned = value.strip()
    approx = bool(APPROX_WORD_RE.search(cleaned) or '?' in cleaned or cleaned.endswith('-'))
    year_match = re.search(r"(\d{4})", cleaned)
    year = int(year_match.group(1)) if year_match else None
    return {"raw": cleaned, "approx": approx, "year": year}


def _split_vitals(vital_text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not vital_text:
        return None, None
    parts = vital_text.split('-', 1)
    if len(parts) == 2:
        birth_part = parts[0].strip() or None
        death_part = parts[1].strip() or None
    else:
        birth_part = vital_text.strip() or None
        death_part = None
    return birth_part, death_part


def _split_name_components(name_part: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    tokens = name_part.split()
    if not tokens:
        return None, None, None
    surname_idx: Optional[int] = None
    for idx, token in enumerate(tokens):
        alpha = re.sub(r"[^A-Za-z]", "", token)
        if alpha and alpha.upper() == alpha:
            surname_idx = idx
    if surname_idx is None:
        if len(tokens) == 1:
            token = tokens[0].strip(',')
            return token or None, None, None
        surname_idx = len(tokens) - 1
    surname_token = tokens[surname_idx]
    surname = surname_token.strip(',')
    if surname == '?':
        surname = None
    given_tokens = tokens[:surname_idx]
    title_tokens = tokens[surname_idx + 1 :]
    given = ' '.join(given_tokens).strip() or None
    title = ' '.join(title_tokens).strip(', ') or None
    return given, surname, title


def _parse_person_entry(text_value: str) -> Dict[str, object]:
    working = text_value.strip()
    vital_match = re.search(r"\(([^)]*)\)", working)
    notes_parts: List[str] = []
    vital_text: Optional[str] = None
    if vital_match:
        vital_text = vital_match.group(1).strip()
        tail = working[vital_match.end():].strip(' ,;')
        if tail:
            notes_parts.append(tail)
        name_part = working[: vital_match.start()].strip()
    else:
        name_part = working
    id_matches = re.findall(r"-(\d+)", name_part)
    name_part = re.sub(r"-\d+(?=\b)", "", name_part)
    name_part = re.sub(r"\s+", " ", name_part).strip(' ,;')
    if id_matches:
        notes_parts.extend([f"ID {match}" for match in id_matches])
    notes = '; '.join(notes_parts) if notes_parts else None
    given, surname, title = _split_name_components(name_part)
    birth_part, death_part = _split_vitals(vital_text)
    birth_info = _build_vital(birth_part)
    death_info = _build_vital(death_part)
    approx = bool(birth_info and birth_info.get("approx")) or bool(death_info and death_info.get("approx"))
    if vital_text:
        trimmed_vitals = vital_text.strip()
        if trimmed_vitals.startswith('-') or trimmed_vitals.endswith('-'):
            approx = True
    if '?' in name_part or (vital_text and '?' in vital_text):
        approx = True
    display_name = name_part or "Unknown"
    birth_year = birth_info.get("year") if birth_info else None
    vitals = {"birth": birth_info, "death": death_info}
    return {
        "display": display_name,
        "given": given,
        "surname": surname,
        "title": title,
        "notes": notes,
        "vitals": vitals,
        "approx": approx,
        "birth_year": birth_year,
    }


def _update_person_location(person: Person, page_index: int, line_index: int, session: Session) -> None:
    changed = False
    if person.page_index != page_index:
        person.page_index = page_index
        changed = True
    if person.line_index != line_index:
        person.line_index = line_index
        changed = True
    if changed:
        session.add(person)


def _family_line_key(source_id: int, page_index: int, line_index: int, principal_id: int, spouse_id: int) -> str:
    payload = f"{source_id}:{page_index}:{line_index}:family:{principal_id}:{spouse_id}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _child_link_key(source_id: int, page_index: int, line_index: int, child_id: int, family_id: int) -> str:
    payload = f"{source_id}:{page_index}:{line_index}:child:{family_id}:{child_id}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


class GenerationContext:
    __slots__ = ("gen", "person", "spouse", "family")

    def __init__(self, gen: int, person: Person) -> None:
        self.gen = gen
        self.person = person
        self.spouse: Optional[Person] = None
        self.family: Optional[Family] = None


@dataclass
class ParseStats:
    people_seen: set
    families_seen: set
    children_seen: set


def parse_ocr_text(
    session: Session,
    *,
    source_id: int,
    pages: List[str],
) -> Dict[str, int]:
    _ensure_person_approx_column(session)

    stats = ParseStats(set(), set(), set())
    generation_stack: List[GenerationContext] = []

    for page_index, line_index, raw_line in iter_lines(pages):
        person_match = PERSON_PATTERN.match(raw_line)
        if person_match:
            gen = int(person_match.group(1))
            text_value = person_match.group(2).strip()

            while generation_stack and generation_stack[-1].gen >= gen:
                generation_stack.pop()

            parent_context = generation_stack[-1] if generation_stack else None
            data = _parse_person_entry(text_value)
            line_key = _make_line_key(source_id, page_index, line_index, raw_line)
            person = Person.upsert_from_parse(
                session,
                source_id,
                data["given"],
                data["surname"],
                name=data["display"],
                gen=gen,
                title=data["title"],
                notes=data["notes"],
                vitals=data["vitals"],
                line_key=line_key,
                approx=data["approx"],
            )
            _update_person_location(person, page_index, line_index, session)
            if person.id:
                stats.people_seen.add(person.id)

            context = GenerationContext(gen, person)
            generation_stack.append(context)

            if parent_context and gen == parent_context.gen + 1:
                family = parent_context.family
                if family is None:
                    family_key = _family_line_key(
                        source_id,
                        page_index,
                        line_index,
                        parent_context.person.id,
                        parent_context.person.id,
                    )
                    family = Family.ensure_for_single_parent(
                        session,
                        source_id,
                        parent_context.person.id,
                        line_key=family_key,
                        approx=bool(parent_context.person.approx),
                    )
                    parent_context.family = family
                if family and family.id:
                    stats.families_seen.add(family.id)
                    link_key = _child_link_key(
                        source_id,
                        page_index,
                        line_index,
                        person.id,
                        family.id,
                    )
                    link = Child.link(
                        session,
                        family.id,
                        person.id,
                        line_key=link_key,
                        approx=data["approx"],
                    )
                    if link.id:
                        stats.children_seen.add(link.id)
                    if data["approx"] and family.approx is not True:
                        family.approx = True
                        session.add(family)
            continue

        spouse_match = SPOUSE_PATTERN.match(raw_line)
        if spouse_match and generation_stack:
            context = generation_stack[-1]
            spouse_text = spouse_match.group(1).strip()
            data = _parse_person_entry(spouse_text)
            line_key = _make_line_key(source_id, page_index, line_index, raw_line)
            spouse = Person.upsert_from_parse(
                session,
                source_id,
                data["given"],
                data["surname"],
                name=data["display"],
                gen=context.gen,
                title=data["title"],
                notes=data["notes"],
                vitals=data["vitals"],
                line_key=line_key,
                approx=data["approx"],
            )
            _update_person_location(spouse, page_index, line_index, session)
            if spouse.id:
                stats.people_seen.add(spouse.id)

            approx_flag = bool(context.person.approx) or data["approx"]
            family = context.family
            if family and family.is_single_parent:
                pair = sorted((context.person.id, spouse.id))
                family.husband_id = pair[0]
                family.wife_id = pair[1]
                family.is_single_parent = False
                if not family.line_key:
                    family.line_key = _family_line_key(
                        source_id,
                        page_index,
                        line_index,
                        pair[0],
                        pair[1],
                    )
                if approx_flag and family.approx is not True:
                    family.approx = True
                session.add(family)
            else:
                family_key = _family_line_key(
                    source_id,
                    page_index,
                    line_index,
                    context.person.id,
                    spouse.id,
                )
                family = Family.upsert_couple(
                    session,
                    source_id,
                    context.person.id,
                    spouse.id,
                    line_key=family_key,
                    approx=approx_flag,
                )
            context.family = family
            context.spouse = spouse
            if family and family.id:
                stats.families_seen.add(family.id)
            if approx_flag and family and family.approx is not True:
                family.approx = True
                session.add(family)
            continue

    session.commit()
    return {
        "people": len(stats.people_seen),
        "families": len(stats.families_seen),
        "children": len(stats.children_seen),
    }


__all__ = ["parse_ocr_text", "normalize_text", "normalize_ocr_text"]
