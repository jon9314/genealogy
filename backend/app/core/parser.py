from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from typing import Dict, Iterator, List, Optional, Tuple

from sqlmodel import Session

from .models import Child, Family, Person

LOGGER = logging.getLogger(__name__)

DASH_SET = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212-"
COLUMN_TOLERANCE = 2

PERSON_LINE = re.compile(
    rf"^(?P<leading>\s*)(?P<gen>\d+)\s*[{DASH_SET}]{{2}}\s+(?P<body>.+)$"
)
SPOUSE_LINE = re.compile(
    rf"^(?P<leading>\s*)sp\s*[{DASH_SET}]\s*(?P<body>.+)$",
    re.IGNORECASE,
)
PAREN_VITAL = re.compile(r"\((?P<body>[^()]*)\)\s*$")

APPROX_TOKEN = re.compile(
    r"(?:\b(?:abt|about|around|ca\.?|circa|before|after|bef\.?|aft\.?|c\.)\b|~|\?)",
    re.IGNORECASE,
)
YEAR_TOKEN = re.compile(r"\b(\d{4})\b")
ID_SUFFIX = re.compile(rf"[{DASH_SET}]\s*(\d+)$")
TITLE_PATTERN = re.compile(
    r"(?<!\w)(?P<title>(?:Lt\.?|Capt\.?|Col\.?|Maj\.?|Rev\.?|Dr\.?|Deacon|Sgt\.?|Gen\.?|General|Prof\.?|Judge|Hon\.?|Elder|Sir|Lady))(?!\w)",
    re.IGNORECASE,
)
NOTE_SEPARATORS = [",", ";", " - ", ": "]


@dataclass
class Vitals:
    raw: str
    year: Optional[int] = None
    approx: bool = False
    place: Optional[str] = None


@dataclass
class ParsedLine:
    kind: str
    text: str
    raw: str
    page_index: int
    line_index: int
    generation: Optional[int] = None
    content_col: Optional[int] = None


@dataclass
class ContextNode:
    generation: int
    person: Person
    surname_hint: Optional[str]
    content_col: int
    family: Optional[Family] = None
    approx: bool = False



_PERSON_APPROX_COLUMN_CHECKED = False


def _ensure_person_approx_column(session: Session) -> None:
    global _PERSON_APPROX_COLUMN_CHECKED
    if _PERSON_APPROX_COLUMN_CHECKED:
        return
    try:
        columns = session.exec(text('PRAGMA table_info(person)')).all()
    except Exception:
        _PERSON_APPROX_COLUMN_CHECKED = True
        return
    has_column = any(row[1] == 'approx' for row in columns)
    if not has_column:
        try:
            session.exec(text('ALTER TABLE person ADD COLUMN approx BOOLEAN'))
            session.commit()
        except OperationalError:
            session.rollback()
        except Exception:
            session.rollback()
    _PERSON_APPROX_COLUMN_CHECKED = True

def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value)
    text = text.replace("\u00AD", "")
    text = re.sub(rf"[{DASH_SET}]", "-", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def iter_lines(pages: List[str]) -> Iterator[Tuple[int, int, str]]:
    for page_index, page in enumerate(pages):
        for line_index, raw in enumerate(page.splitlines()):
            yield page_index, line_index, raw.rstrip("\r\n")


def has_approx(value: Optional[str]) -> bool:
    if not value:
        return False
    text = value.strip()
    if not text:
        return False
    if APPROX_TOKEN.search(text):
        return True
    normalized = re.sub(rf"[{DASH_SET}]", "-", text)
    if normalized.endswith("-") or normalized.startswith("-"):
        return True
    return False


def _normalize_for_key(value: Optional[str]) -> str:
    if not value:
        return ""
    return normalize_text(value).lower()


def extract_titles(text: str) -> Tuple[str, Optional[str]]:
    titles: List[str] = []

    def _collect(match: re.Match[str]) -> str:
        titles.append(match.group("title"))
        return " "

    stripped = TITLE_PATTERN.sub(_collect, text)
    cleaned = normalize_text(stripped)
    if not titles:
        return cleaned, None
    ordered: List[str] = []
    seen: set[str] = set()
    for title in titles:
        if title not in seen:
            ordered.append(title)
            seen.add(title)
    return cleaned, " ".join(ordered)


def extract_id_suffix(text: str) -> Tuple[str, Optional[str]]:
    match = ID_SUFFIX.search(text)
    if not match:
        return text, None
    cleaned = ID_SUFFIX.sub("", text).strip(" ,;:-")
    return cleaned, match.group(1)


def split_display_and_notes(text: str) -> Tuple[str, Optional[str]]:
    working = text.strip()
    for separator in NOTE_SEPARATORS:
        if separator in working:
            head, tail = working.split(separator, 1)
            head = head.strip()
            tail = tail.strip()
            if tail and tail[0].islower():
                return head, tail
    return working, None


def _looks_like_vital(content: str) -> bool:
    if not content:
        return False
    if YEAR_TOKEN.search(content):
        return True
    if APPROX_TOKEN.search(content):
        return True
    if "?" in content:
        return True
    if re.search(rf"[{DASH_SET}]", content):
        left, right = re.split(rf"[{DASH_SET}]", content, maxsplit=1)
        return bool(left.strip()) or bool(right.strip())
    return False


def _split_vital_content(content: str) -> Tuple[Optional[str], Optional[str], bool, bool]:
    normalized = re.sub(rf"[{DASH_SET}]", "-", content)
    if "-" not in normalized:
        trimmed = normalized.strip()
        return trimmed or None, None, False, False
    left, right = normalized.split("-", 1)
    left = left.strip()
    right = right.strip()
    birth_missing = not left
    death_missing = not right
    return left or None, right or None, birth_missing, death_missing


def _make_vitals(raw_value: str, *, force_approx: bool = False) -> Vitals:
    cleaned = normalize_text(raw_value)
    year_match = YEAR_TOKEN.search(cleaned)
    year = int(year_match.group(1)) if year_match else None
    approx = force_approx or has_approx(raw_value)
    return Vitals(raw=cleaned, year=year, approx=approx)


def parse_vitals(chunk: str) -> Tuple[str, Dict[str, Optional[Vitals]], Optional[str]]:
    working = chunk.strip()
    vitals: Dict[str, Optional[Vitals]] = {"birth": None, "death": None}

    remainder = working
    while True:
        match = PAREN_VITAL.search(remainder)
        if not match:
            break
        content = match.group("body").strip()
        if not _looks_like_vital(content):
            break
        birth_raw, death_raw, birth_missing, death_missing = _split_vital_content(content)
        if birth_raw and vitals["birth"] is None:
            vitals["birth"] = _make_vitals(birth_raw, force_approx=death_missing)
        if death_raw and vitals["death"] is None:
            vitals["death"] = _make_vitals(death_raw, force_approx=birth_missing)
        remainder = remainder[: match.start()].rstrip()

    normalized = normalize_text(remainder)
    display, inline_note = split_display_and_notes(normalized)
    return display, vitals, inline_note


def vitals_are_approx(vitals: Dict[str, Optional[Vitals]]) -> bool:
    return any(value is not None and value.approx for value in vitals.values())


def parse_name(text: str, inferred_surname: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    work = normalize_text(text)
    work = re.sub(r"\([^)]*\)$", "", work).strip()
    raw_tokens = work.replace(",", " , ").split()
    tokens = [token for token in raw_tokens if token not in {",", "?"}]

    if "," in work:
        parts = [part.strip() for part in work.split(",", 1)]
        if parts[0] and len(parts[0].split()) == 1:
            surname = parts[0]
            given_tokens = [token for token in parts[1].split() if token not in {",", "?"}]
            given = " ".join(given_tokens) if given_tokens else None
            return given, surname, None

    if len(tokens) >= 2:
        given = " ".join(tokens[:-1])
        surname = tokens[-1]
    elif tokens:
        given = tokens[0]
        surname = inferred_surname
    else:
        given = None
        surname = inferred_surname
    return given, surname, None


def line_key(
    source_id: int,
    parent_path: Tuple[str, ...],
    text: str,
    *,
    generation: Optional[int] = None,
    birth: Optional[str] = None,
    death: Optional[str] = None,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    page_index: Optional[int] = None,
    line_index: Optional[int] = None,
    extra: Optional[str] = None,
) -> str:
    parent = "/".join(_normalize_for_key(part) for part in parent_path)
    components = [
        str(source_id),
        parent,
        _normalize_for_key(text),
        _normalize_for_key(extra),
        str(generation or ""),
        _normalize_for_key(birth),
        _normalize_for_key(death),
        _normalize_for_key(title),
        _normalize_for_key(notes),
        f"{page_index if page_index is not None else ''}:{line_index if line_index is not None else ''}",
    ]
    return hashlib.sha1("|".join(components).encode("utf-8")).hexdigest()


def stack_parent_path(stack: List[ContextNode]) -> Tuple[str, ...]:
    parts: List[str] = []
    for node in stack:
        name = node.person.given or node.person.surname or node.person.name
        if name:
            parts.append(name)
    return tuple(parts)


def find_spouse_context(
    stack: List[ContextNode],
    current_subject: Optional[ContextNode],
    column: Optional[int],
) -> Optional[ContextNode]:
    candidates: List[ContextNode] = []
    if current_subject and current_subject in stack:
        candidates.append(current_subject)
    for node in reversed(stack):
        if node is current_subject:
            continue
        candidates.append(node)
    for node in candidates:
        if column is None:
            return node
        if abs(node.content_col - column) <= COLUMN_TOLERANCE:
            return node
    return candidates[0] if candidates else None


def classify_line(
    line: str,
    *,
    page_index: int,
    line_index: int,
) -> Optional[ParsedLine]:
    raw = line.rstrip()
    if not raw.strip():
        return None
    person_match = PERSON_LINE.match(raw)
    if person_match:
        body_start = person_match.start("body")
        generation = int(person_match.group("gen"))
        body = person_match.group("body")
        return ParsedLine(
            kind="person",
            text=normalize_text(body),
            raw=raw,
            page_index=page_index,
            line_index=line_index,
            generation=generation,
            content_col=body_start,
        )
    spouse_match = SPOUSE_LINE.match(raw)
    if spouse_match:
        body_start = spouse_match.start("body")
        body = spouse_match.group("body")
        return ParsedLine(
            kind="spouse",
            text=normalize_text(body),
            raw=raw,
            page_index=page_index,
            line_index=line_index,
            content_col=body_start,
        )
    return ParsedLine(
        kind="note",
        text=normalize_text(raw),
        raw=raw,
        page_index=page_index,
        line_index=line_index,
    )


def parse_ocr_text(
    session: Session,
    *,
    source_id: int,
    pages: List[str],
) -> Dict[str, int]:
    _ensure_person_approx_column(session)

    generation_stack: List[ContextNode] = []
    current_subject: Optional[ContextNode] = None

    people_seen: set[int] = set()
    families_seen: set[int] = set()
    children_seen: set[int] = set()

    for page_index, line_index, raw_line in iter_lines(pages):
        parsed = classify_line(raw_line, page_index=page_index, line_index=line_index)
        if parsed is None:
            continue
        if parsed.kind == "note":
            continue

        if parsed.kind == "person":
            while generation_stack and parsed.generation is not None and generation_stack[-1].generation >= parsed.generation:
                generation_stack.pop()

            parent_context = generation_stack[-1] if generation_stack else None
            parent_path = stack_parent_path(generation_stack)

            core_text, vitals, inline_note = parse_vitals(parsed.text)
            name_without_titles, title = extract_titles(core_text)
            name_without_ids, id_suffix = extract_id_suffix(name_without_titles)
            display_name = name_without_ids

            notes_parts: List[str] = []
            if id_suffix:
                notes_parts.append(f"ID {id_suffix}")
            if inline_note:
                notes_parts.append(inline_note)
            notes_value = "; ".join(notes_parts) if notes_parts else None

            approx_flag = vitals_are_approx(vitals) or has_approx(parsed.text)

            surname_hint = parent_context.surname_hint if parent_context else None
            given, surname, _ = parse_name(display_name, surname_hint)
            if not surname and surname_hint:
                surname = surname_hint

            generation_value = parsed.generation or ((parent_context.generation + 1) if parent_context else 1)

            person_key = line_key(
                source_id,
                parent_path,
                display_name or parsed.text,
                generation=generation_value,
                birth=vitals["birth"].raw if vitals["birth"] else None,
                death=vitals["death"].raw if vitals["death"] else None,
                title=title,
                notes=notes_value,
                page_index=parsed.page_index,
                line_index=parsed.line_index,
                extra="person",
            )

            person = Person.upsert_from_parse(
                session,
                source_id,
                given,
                surname,
                name=display_name or parsed.text,
                gen=generation_value,
                title=title,
                notes=notes_value,
                vitals={
                    "birth": vitals["birth"].__dict__ if vitals["birth"] else None,
                    "death": vitals["death"].__dict__ if vitals["death"] else None,
                },
                line_key=person_key,
                approx=approx_flag,
            )
            if person.id:
                people_seen.add(person.id)

            node = ContextNode(
                generation=generation_value,
                person=person,
                surname_hint=person.surname or surname_hint,
                content_col=parsed.content_col or 0,
                family=None,
                approx=bool(person.approx),
            )
            generation_stack.append(node)
            current_subject = node

            if parent_context and person.id and parent_context.person.id and generation_value == parent_context.generation + 1:
                family = parent_context.family
                if family is None:
                    family_label = (
                        parent_context.person.name
                        or parent_context.person.given
                        or parent_context.person.surname
                        or "parent"
                    )
                    family_key = line_key(
                        source_id,
                        parent_path,
                        f"{family_label} family",
                        generation=parent_context.generation,
                        notes=notes_value,
                        page_index=parsed.page_index,
                        line_index=parsed.line_index,
                        extra="family",
                    )
                    family = Family.ensure_for_single_parent(
                        session,
                        source_id,
                        parent_context.person.id,
                        line_key=family_key,
                        approx=bool(parent_context.person.approx) or approx_flag,
                    )
                    parent_context.family = family
                if family:
                    if family.id:
                        families_seen.add(family.id)
                    link_key = line_key(
                        source_id,
                        parent_path,
                        display_name or parsed.text,
                        generation=generation_value,
                        birth=vitals["birth"].raw if vitals["birth"] else None,
                        death=vitals["death"].raw if vitals["death"] else None,
                        title=title,
                        notes=notes_value,
                        page_index=parsed.page_index,
                        line_index=parsed.line_index,
                        extra="child-link",
                    )
                    link = Child.link(
                        session,
                        family.id,
                        person.id,
                        line_key=link_key,
                        approx=approx_flag,
                    )
                    if link.id:
                        children_seen.add(link.id)
                    if approx_flag and family.approx is not True:
                        family.approx = True
                        session.add(family)
            continue

        if parsed.kind == "spouse":
            target_context = find_spouse_context(generation_stack, current_subject, parsed.content_col)
            if not target_context or not target_context.person.id:
                continue
            parent_path = stack_parent_path(generation_stack)

            core_text, vitals, inline_note = parse_vitals(parsed.text)
            name_without_titles, title = extract_titles(core_text)
            name_without_ids, id_suffix = extract_id_suffix(name_without_titles)
            display_name = name_without_ids

            notes_parts: List[str] = []
            if id_suffix:
                notes_parts.append(f"ID {id_suffix}")
            if inline_note:
                notes_parts.append(inline_note)
            notes_value = "; ".join(notes_parts) if notes_parts else None

            approx_flag = vitals_are_approx(vitals) or has_approx(parsed.text)

            given, surname, _ = parse_name(display_name, None)
            generation_value = target_context.generation

            principal_label = (
                target_context.person.given
                or target_context.person.surname
                or target_context.person.name
                or "principal"
            )
            anchored_path = parent_path + (principal_label,)

            spouse_key = line_key(
                source_id,
                anchored_path,
                display_name or parsed.text,
                generation=generation_value,
                birth=vitals["birth"].raw if vitals["birth"] else None,
                death=vitals["death"].raw if vitals["death"] else None,
                title=title,
                notes=notes_value,
                page_index=parsed.page_index,
                line_index=parsed.line_index,
                extra="spouse",
            )

            spouse = Person.upsert_from_parse(
                session,
                source_id,
                given,
                surname,
                name=display_name or parsed.text,
                gen=generation_value,
                title=title,
                notes=notes_value,
                vitals={
                    "birth": vitals["birth"].__dict__ if vitals["birth"] else None,
                    "death": vitals["death"].__dict__ if vitals["death"] else None,
                },
                line_key=spouse_key,
                approx=approx_flag,
            )
            if spouse.id:
                people_seen.add(spouse.id)

            family_label = (
                f"{target_context.person.name or (target_context.person.given or target_context.person.surname or '')} = "
                f"{display_name or parsed.text}"
            )
            family_key = line_key(
                source_id,
                parent_path,
                family_label,
                generation=generation_value,
                birth=vitals["birth"].raw if vitals["birth"] else None,
                death=vitals["death"].raw if vitals["death"] else None,
                title=title,
                notes=notes_value,
                page_index=parsed.page_index,
                line_index=parsed.line_index,
                extra="family",
            )
            family = Family.upsert_couple(
                session,
                source_id,
                target_context.person.id,
                spouse.id if spouse.id else None,
                line_key=family_key,
                approx=bool(target_context.person.approx) or approx_flag,
            )
            target_context.family = family
            current_subject = target_context
            if family and family.id:
                families_seen.add(family.id)
            if family and approx_flag and family.approx is not True:
                family.approx = True
                session.add(family)
            continue

    session.commit()
    return {
        "people": len(people_seen),
        "families": len(families_seen),
        "children": len(children_seen),
    }


__all__ = ["parse_ocr_text", "normalize_text"]
