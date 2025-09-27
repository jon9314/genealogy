from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from sqlmodel import Session

from .models import Child, Family, Person

LOGGER = logging.getLogger(__name__)

DASH_SET = "\u2012\u2013\u2014\u2015\u2212-"
BULLET_SET = "\u2022\u2023\u2043"

GEN_TOKEN = re.compile(
    rf"^([ \t]*)(?:(?P<num>\d+|[IVXLCDM]+|[A-Za-z])[\.\):]|[\-]?\d+|#[0-9]+|\([0-9]+\))[ \t]+(?P<body>.+)$",
    re.IGNORECASE,
)
SPOUSE_TOKEN = re.compile(
    r"\b(?:m\.\s*|sp:?\s*|spouse:?\s*|married(?: to)?:?\s*|wife:?\s*|husband:?\s*)(?P<body>.+)$",
    re.IGNORECASE,
)
CHILDREN_HEAD = re.compile(r"\b(?:children|issue)\b[:\-]?\s*(?P<body>.*)$", re.IGNORECASE)
BULLET_CHILD = re.compile(
    rf"^[ \t]*(?:[{BULLET_SET}-]|\d+[\.\)]|[A-Za-z][\.\)])\s+(?P<body>.+)$"
)
ID_SUFFIX = re.compile(rf"[{DASH_SET}]\s*(\d+)$")
INLINE_VITAL = re.compile(
    r"\b(?P<tag>b\.\s*|born\s*|bp\.\s*|bapt(?:ised|ized)?\.?\s*|chr(?:istened)?\.?\s*)(?P<body>[^;,\)]+)",
    re.IGNORECASE,
)
INLINE_DEATH = re.compile(
    r"\b(?P<tag>d\.\s*|died\s*|bur(?:ied)?\.?\s*)(?P<body>[^;,\)]+)",
    re.IGNORECASE,
)
NOTE_SPLIT = re.compile(r"[;,]")

APPROX_TOKEN = re.compile(r"\b(?:abt|about|ca\.?|circa|~|before|after|bef\.?|aft\.?)\b", re.IGNORECASE)
YEAR_TOKEN = re.compile(r"\b(\d{4})\b")
PLACE_SPLIT = re.compile(r"\s*,\s*")


def roman_to_int(value: str) -> Optional[int]:
    numerals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for char in reversed(value.upper()):
        current = numerals.get(char)
        if current is None:
            return None
        if current < prev:
            total -= current
        else:
            total += current
            prev = current
    return total if total > 0 else None


def token_to_generation(token: Optional[str], stack_depth: int) -> int:
    if not token:
        return stack_depth + 1
    token_upper = token.upper()
    if token_upper.isdigit():
        try:
            return int(token_upper)
        except ValueError:
            pass
    if re.fullmatch(r"[IVXLCDM]+", token_upper):
        roman_value = roman_to_int(token_upper)
        if roman_value:
            return roman_value
    if len(token_upper) == 1 and token_upper.isalpha():
        return ord(token_upper) - ord("A") + 1
    return stack_depth + 1


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
    indent: int
    token: Optional[str] = None
    spouses: List[str] = field(default_factory=list)
    inline_children: List[str] = field(default_factory=list)


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value)
    text = text.replace("\u00AD", "")
    text = re.sub(rf"[{DASH_SET}]", "-", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def join_wrapped_lines(lines: Iterable[str]) -> Iterator[str]:
    buffer: List[str] = []
    for raw in lines:
        cleaned = normalize_text(raw)
        if not cleaned:
            if buffer:
                yield " ".join(buffer)
                buffer.clear()
            continue
        if buffer and not buffer[-1].endswith(tuple(".;:")) and cleaned and cleaned[:1].islower():
            buffer.append(cleaned)
        else:
            if buffer:
                yield " ".join(buffer)
                buffer.clear()
            buffer.append(cleaned)
    if buffer:
        yield " ".join(buffer)


def classify_line(line: str) -> ParsedLine:
    match = GEN_TOKEN.match(line)
    if match:
        indent = len(match.group(1).replace("\t", "  "))
        body = match.group("body")
        token = match.group("num")
        return ParsedLine(kind="person", text=body, indent=indent, token=token)

    children_match = CHILDREN_HEAD.search(line)
    if children_match:
        rest = children_match.group("body") or ""
        inline = [normalize_text(part) for part in NOTE_SPLIT.split(rest) if normalize_text(part)]
        return ParsedLine(kind="children_head", text=line, indent=0, inline_children=inline)

    bullet_match = BULLET_CHILD.match(line)
    if bullet_match:
        return ParsedLine(kind="child", text=bullet_match.group("body"), indent=0)

    spouse_match = SPOUSE_TOKEN.search(line)
    if spouse_match:
        return ParsedLine(kind="spouse", text=spouse_match.group("body"), indent=0)

    return ParsedLine(kind="note", text=line, indent=0)


def split_spouses(text: str) -> Tuple[str, List[str]]:
    matches = list(SPOUSE_TOKEN.finditer(text))
    if not matches:
        return text.strip(), []
    primary = text[: matches[0].start()].strip()
    spouses = [normalize_text(match.group("body")) for match in matches]
    return primary or text, spouses


def _remove_span(text: str, start: int, end: int) -> str:
    return text[:start] + text[end:]


def parse_vitals(chunk: str) -> Tuple[str, Dict[str, Optional[Vitals]]]:
    """Extract birth/death vitals and return the remaining text."""

    working = chunk
    data: Dict[str, Optional[Vitals]] = {"birth": None, "death": None}

    for regex, key in ((INLINE_VITAL, "birth"), (INLINE_DEATH, "death")):
        while True:
            match = regex.search(working)
            if not match:
                break
            raw = normalize_text(match.group("body"))
            approx = bool(APPROX_TOKEN.search(raw))
            year_match = YEAR_TOKEN.search(raw)
            year = int(year_match.group(1)) if year_match else None
            parts = PLACE_SPLIT.split(raw)
            place = ", ".join(parts[1:]) if len(parts) > 1 else None
            if data[key] is None:
                data[key] = Vitals(raw=raw, year=year, approx=approx, place=place)
            start, end = match.span()
            working = _remove_span(working, start, end)

    # Remove leftover empty parentheses and extra punctuation
    working = re.sub(r"\(\s*\)", "", working)
    working = normalize_text(re.sub(r"[;,]+", " ", working)).strip(",;:- ")

    return working, data


def parse_name(text: str, inferred_surname: Optional[str]) -> Tuple[str, str, Optional[str]]:
    work = normalize_text(text)
    work = ID_SUFFIX.sub("", work).strip(",")
    if "," in work and len(work.split(",", 1)[0].split()) == 1:
        surname, rest = work.split(",", 1)
        return rest.strip(), surname.strip(), None

    tokens = work.split()
    if not tokens:
        return work, inferred_surname or "", None
    if inferred_surname and len(tokens) == 1:
        return work, inferred_surname, None
    if len(tokens) >= 2:
        return " ".join(tokens[:-1]), tokens[-1], None
    return work, inferred_surname or "", None


def line_key(source_id: int, parent_path: Tuple[str, ...], text: str) -> str:
    normalized = normalize_text(text).lower()
    parent = "/".join(parent_path)
    return hashlib.sha1(f"{source_id}|{parent}|{normalized}".encode()).hexdigest()


@dataclass
class ContextNode:
    indent: int
    person: Person
    surname_hint: Optional[str]
    family: Optional[Family] = None


def stack_parent_path(stack: List[ContextNode]) -> Tuple[str, ...]:
    parts: List[str] = []
    for node in stack:
        name = node.person.given or node.person.surname or node.person.name
        if name:
            parts.append(name)
    return tuple(parts)


def iter_lines(pages: List[str]) -> Iterator[str]:
    for page in pages:
        for line in page.splitlines():
            yield line


def parse_ocr_text(
    session: Session,
    *,
    source_id: int,
    pages: List[str],
) -> Dict[str, int]:
    generation_stack: List[ContextNode] = []
    current_family: Optional[Family] = None

    people_seen: set[int] = set()
    families_seen: set[int] = set()
    children_seen: set[int] = set()

    for raw_line in join_wrapped_lines(iter_lines(pages)):
        parsed = classify_line(raw_line)
        text = parsed.text

        if parsed.kind == "person":
            primary_text, spouse_chunks = split_spouses(text)
            primary_clean, vitals = parse_vitals(primary_text)
            surname_hint = generation_stack[-1].surname_hint if generation_stack else None
            given, surname, _ = parse_name(primary_clean, surname_hint)
            generation = token_to_generation(parsed.token, len(generation_stack))

            while generation_stack and generation_stack[-1].indent >= parsed.indent:
                generation_stack.pop()
            parent_path = stack_parent_path(generation_stack)
            person = Person.upsert_from_parse(
                session,
                source_id,
                given,
                surname,
                name=primary_clean,
                gen=generation,
                notes=raw_line,
                vitals={
                    "birth": vitals["birth"].__dict__ if vitals["birth"] else None,
                    "death": vitals["death"].__dict__ if vitals["death"] else None,
                },
                line_key=line_key(source_id, parent_path, primary_clean),
            )
            if person.id:
                people_seen.add(person.id)

            current_family = None
            generation_stack.append(
                ContextNode(
                    indent=parsed.indent,
                    person=person,
                    surname_hint=person.surname or surname_hint,
                )
            )

            for spouse_text in spouse_chunks:
                spouse_clean, sp_vitals = parse_vitals(spouse_text)
                sg, ss, _ = parse_name(spouse_clean, None)
                parent_path = stack_parent_path(generation_stack)
                spouse = Person.upsert_from_parse(
                    session,
                    source_id,
                    sg,
                    ss,
                    name=spouse_clean,
                    gen=person.gen,
                    notes=spouse_text,
                    vitals={
                        "birth": sp_vitals["birth"].__dict__ if sp_vitals["birth"] else None,
                        "death": sp_vitals["death"].__dict__ if sp_vitals["death"] else None,
                    },
                    line_key=line_key(source_id, parent_path + (person.given or "",), spouse_clean),
                )
                if spouse.id:
                    people_seen.add(spouse.id)
                family = Family.upsert_couple(session, source_id, person.id, spouse.id)
                current_family = family
                if family.id:
                    families_seen.add(family.id)
                generation_stack[-1].family = family

            continue

        if parsed.kind == "spouse" and generation_stack:
            principal = generation_stack[-1].person
            spouse_clean, sp_vitals = parse_vitals(parsed.text)
            sg, ss, _ = parse_name(spouse_clean, None)
            parent_path = stack_parent_path(generation_stack)
            spouse = Person.upsert_from_parse(
                session,
                source_id,
                sg,
                ss,
                name=spouse_clean,
                gen=principal.gen,
                notes=raw_line,
                vitals={
                    "birth": sp_vitals["birth"].__dict__ if sp_vitals["birth"] else None,
                    "death": sp_vitals["death"].__dict__ if sp_vitals["death"] else None,
                },
                line_key=line_key(source_id, parent_path + (principal.given or "",), spouse_clean),
            )
            if spouse.id:
                people_seen.add(spouse.id)
            current_family = Family.upsert_couple(session, source_id, principal.id, spouse.id)
            generation_stack[-1].family = current_family
            if current_family.id:
                families_seen.add(current_family.id)
            continue

        if parsed.kind == "children_head":
            if parsed.inline_children and generation_stack:
                node = generation_stack[-1]
                principal = node.person
                family = current_family or node.family or Family.ensure_for_single_parent(
                    session, source_id, principal.id
                )
                if family is None:
                    continue
                current_family = family
                generation_stack[-1].family = family
                if family.id:
                    families_seen.add(family.id)
                parent_path = stack_parent_path(generation_stack)
                for child_text in parsed.inline_children:
                    child_clean, child_vitals = parse_vitals(child_text)
                    cg, cs, _ = parse_name(child_clean, node.surname_hint)
                    parent_gen = node.person.gen if node.person.gen is not None else len(generation_stack)
                    child_gen = parent_gen + 1
                    if node.person.gen is None:
                        child_gen = token_to_generation(None, len(generation_stack))
                    child = Person.upsert_from_parse(
                        session,
                        source_id,
                        cg,
                        cs,
                        name=child_clean,
                        gen=child_gen,
                        notes=child_text,
                        vitals={
                            "birth": child_vitals["birth"].__dict__ if child_vitals["birth"] else None,
                            "death": child_vitals["death"].__dict__ if child_vitals["death"] else None,
                        },
                        line_key=line_key(source_id, parent_path + (principal.given or "",), child_clean),
                    )
                    if child.id:
                        people_seen.add(child.id)
                    link = Child.link(session, family.id, child.id)
                    if link.id:
                        children_seen.add(link.id)
            continue

        if parsed.kind == "child" and generation_stack:
            node = generation_stack[-1]
            principal = node.person
            family = current_family or node.family or Family.ensure_for_single_parent(
                session, source_id, principal.id
            )
            if family is None:
                continue
            child_clean, child_vitals = parse_vitals(parsed.text)
            cg, cs, _ = parse_name(child_clean, node.surname_hint)
            parent_path = stack_parent_path(generation_stack)
            parent_gen = principal.gen if principal.gen is not None else len(generation_stack)
            child_gen = parent_gen + 1
            if principal.gen is None:
                child_gen = token_to_generation(None, len(generation_stack))
            child = Person.upsert_from_parse(
                session,
                source_id,
                cg,
                cs,
                name=child_clean,
                gen=child_gen,
                notes=parsed.text,
                vitals={
                    "birth": child_vitals["birth"].__dict__ if child_vitals["birth"] else None,
                    "death": child_vitals["death"].__dict__ if child_vitals["death"] else None,
                },
                line_key=line_key(source_id, parent_path + (principal.given or "",), child_clean),
            )
            if child.id:
                people_seen.add(child.id)
            generation_stack[-1].family = family
            if family.id:
                families_seen.add(family.id)
            link = Child.link(session, family.id, child.id)
            if link.id:
                children_seen.add(link.id)
            continue

        if parsed.kind == "note":
            continue

    session.commit()
    return {
        "people": len(people_seen),
        "families": len(families_seen),
        "children": len(children_seen),
    }


__all__ = ["parse_ocr_text", "normalize_text"]
