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
LEADING_WHITESPACE = re.compile(r"^[ \t]*")
EQUAL_SPLIT = re.compile(r"\s*=\s*")
EQUAL_LINE = re.compile(r"^[ \t]*=\s*(?P<body>.+)$")
ID_SUFFIX = re.compile(rf"[~{DASH_SET}]\s*(\d+)$")
INLINE_VITAL = re.compile(
    r"\b(?P<tag>b\.\s*|born\s*|bp\.\s*|bapt(?:ised|ized)?\.?\s*|chr(?:istened)?\.?\s*)(?P<body>[^;,\)]+)",
    re.IGNORECASE,
)
INLINE_DEATH = re.compile(
    r"\b(?P<tag>d\.\s*|died\s*|bur(?:ied)?\.?\s*)(?P<body>[^;,\)]+)",
    re.IGNORECASE,
)
NOTE_SPLIT = re.compile(r"[;,]")

APPROX_TOKEN = re.compile(r"(?:\b(?:abt|about|ca\.?|circa|before|after|bef\.?|aft\.?)\b|~)", re.IGNORECASE)
YEAR_TOKEN = re.compile(r"\b(\d{4})\b")
def has_approx(value: str) -> bool:
    if not value:
        return False
    return bool(APPROX_TOKEN.search(value))


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
        leading_match = re.match(r"^[ \t]*", raw)
        leading = leading_match.group(0) if leading_match else ""
        content = raw[len(leading):]
        cleaned_content = normalize_text(content)
        if not cleaned_content:
            if buffer:
                yield " ".join(buffer)
                buffer.clear()
            continue
        normalized_line = (leading + cleaned_content).rstrip()
        if buffer and not buffer[-1].rstrip().endswith(tuple(".;:")) and cleaned_content[:1].islower():
            buffer.append(normalized_line)
        else:
            if buffer:
                yield " ".join(buffer)
                buffer.clear()
            buffer.append(normalized_line)
    if buffer:
        yield " ".join(buffer)


def classify_line(line: str) -> ParsedLine:
    indent_match = LEADING_WHITESPACE.match(line)
    indent = len(indent_match.group(0).replace("	", "  ")) if indent_match else 0

    match = GEN_TOKEN.match(line)
    if match:
        indent = len(match.group(1).replace("	", "  "))
        body = normalize_text(match.group("body"))
        token = match.group("num")
        return ParsedLine(kind="person", text=body, indent=indent, token=token)

    equals_line = EQUAL_LINE.match(line)
    if equals_line:
        body = normalize_text(equals_line.group("body"))
        return ParsedLine(kind="spouse", text=body, indent=indent)

    children_match = CHILDREN_HEAD.search(line)
    if children_match:
        rest = children_match.group("body") or ""
        inline = split_inline_children_text(rest)
        return ParsedLine(
            kind="children_head",
            text=normalize_text(line),
            indent=indent,
            inline_children=inline,
        )

    bullet_match = BULLET_CHILD.match(line)
    if bullet_match:
        body = normalize_text(bullet_match.group("body"))
        return ParsedLine(kind="child", text=body, indent=indent)

    spouse_match = SPOUSE_TOKEN.search(line)
    if spouse_match:
        body = normalize_text(spouse_match.group("body"))
        return ParsedLine(kind="spouse", text=body, indent=indent)

    return ParsedLine(kind="note", text=normalize_text(line), indent=indent)


def split_spouses(text: str) -> Tuple[str, List[str]]:
    if "=" in text:
        parts: List[str] = []
        for chunk in EQUAL_SPLIT.split(text):
            normalized = normalize_text(chunk)
            if normalized:
                parts.append(normalized)
        if len(parts) >= 2:
            return parts[0], parts[1:]
    matches = list(SPOUSE_TOKEN.finditer(text))
    if not matches:
        return text.strip(), []
    primary = text[: matches[0].start()].strip()
    spouses = [normalize_text(match.group("body")) for match in matches]
    primary_clean = normalize_text(primary) if primary else normalize_text(text)
    return primary_clean, spouses


def split_inline_children_text(text: str) -> List[str]:
    working = normalize_text(text)
    working = re.sub(rf"[{BULLET_SET}]", "-", working)
    results: List[str] = []
    current = ""
    depth = 0
    i = 0
    length = len(working)

    while i < length:
        ch = working[i]
        if ch == "(":
            depth += 1
        elif ch == ")" and depth > 0:
            depth -= 1
        if depth == 0:
            if ch == "-" and i + 1 < length and working[i + 1] == " ":
                piece = current.strip()
                if piece:
                    piece = re.sub(r"^(?:children|issue)[: ]+", "", piece, flags=re.IGNORECASE)
                    if piece:
                        results.append(piece)
                current = ""
                i += 2
                continue
            if ch.isdigit():
                j = i
                while j < length and working[j].isdigit():
                    j += 1
                if j < length and working[j] in ")." and j + 1 < length and working[j + 1] == " ":
                    piece = current.strip()
                    if piece:
                        piece = re.sub(r"^(?:children|issue)[: ]+", "", piece, flags=re.IGNORECASE)
                        if piece:
                            results.append(piece)
                    current = ""
                    i = j + 2
                    continue
        current += ch
        i += 1

    piece = current.strip()
    if piece:
        piece = re.sub(r"^(?:children|issue)[: ]+", "", piece, flags=re.IGNORECASE)
        if piece:
            results.append(piece)

    return [value for value in (item.strip() for item in results) if value]


def _remove_span(text: str, start: int, end: int) -> str:
    return text[:start] + text[end:]


def parse_vitals(chunk: str) -> Tuple[str, Dict[str, Optional[Vitals]]]:
    working = chunk
    data: Dict[str, Optional[Vitals]] = {"birth": None, "death": None}

    for regex, key in ((INLINE_VITAL, "birth"), (INLINE_DEATH, "death")):
        while True:
            match = regex.search(working)
            if not match:
                break
            raw_body = match.group("body")
            raw_clean = normalize_text(raw_body)
            approx = has_approx(raw_body)
            year_match = YEAR_TOKEN.search(raw_clean)
            year = int(year_match.group(1)) if year_match else None
            start, end = match.span()
            span_end = end
            tail = working[span_end:]
            location_text = None
            if tail.startswith(","):
                span_end += 1
                while span_end < len(working) and working[span_end] == " ":
                    span_end += 1
                loc_start = span_end
                while span_end < len(working) and working[span_end] not in ";)":
                    span_end += 1
                location_text = normalize_text(working[loc_start:span_end])
            if data[key] is None:
                stored_raw = raw_clean if not location_text else f"{raw_clean}, {location_text}"
                data[key] = Vitals(raw=stored_raw, year=year, approx=approx, place=location_text)
            working = _remove_span(working, start, span_end)

    working = re.sub(r"\(\s*[,;:-]*\s*\)", "", working)
    working = re.sub(r"\(\s*\)", "", working)
    working = normalize_text(re.sub(r"[;,]+", " ", working)).strip(",;:- ")

    return working, data


def vitals_are_approx(vitals: Dict[str, Optional[Vitals]]) -> bool:
    return any(value is not None and value.approx for value in vitals.values())


def parse_name(text: str, inferred_surname: Optional[str]) -> Tuple[str, str, Optional[str]]:
    work = normalize_text(text)
    work = ID_SUFFIX.sub("", work).strip(",")
    work = re.sub(r"\([^)]*\)$", "", work).strip()
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
            while generation_stack and generation_stack[-1].indent >= parsed.indent:
                generation_stack.pop()

            parent_path = stack_parent_path(generation_stack)
            primary_text, spouse_chunks = split_spouses(text)
            primary_clean, vitals = parse_vitals(primary_text)
            primary_approx = vitals_are_approx(vitals)
            surname_hint = generation_stack[-1].surname_hint if generation_stack else None
            given, surname, _ = parse_name(primary_clean, surname_hint)
            if not surname and surname_hint:
                surname = surname_hint
            generation = token_to_generation(parsed.token, len(generation_stack))

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
                approx=primary_approx,
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
                spouse_approx = vitals_are_approx(sp_vitals)
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
                    line_key=line_key(
                        source_id,
                        parent_path + (person.given or "",),
                        spouse_clean,
                    ),
                    approx=spouse_approx,
                )
                if spouse.id:
                    people_seen.add(spouse.id)
                family_label = f"{person.name or primary_clean} = {spouse_clean}"
                family_key = line_key(source_id, parent_path, family_label)
                family = Family.upsert_couple(
                    session,
                    source_id,
                    person.id,
                    spouse.id,
                    line_key=family_key,
                    approx=primary_approx or spouse_approx,
                )
                current_family = family
                if family.id:
                    families_seen.add(family.id)
                generation_stack[-1].family = family

            continue

        if parsed.kind == "spouse" and generation_stack:
            principal = generation_stack[-1].person
            spouse_clean, sp_vitals = parse_vitals(parsed.text)
            spouse_approx = vitals_are_approx(sp_vitals)
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
                line_key=line_key(
                    source_id,
                    parent_path + (principal.given or "",),
                    spouse_clean,
                ),
                approx=spouse_approx,
            )
            if spouse.id:
                people_seen.add(spouse.id)
            family_label = f"{principal.name or (principal.given or principal.surname or '')} = {spouse_clean}"
            family_key = line_key(source_id, parent_path, family_label)
            family = Family.upsert_couple(
                session,
                source_id,
                principal.id,
                spouse.id,
                line_key=family_key,
                approx=bool(principal.approx) or spouse_approx,
            )
            generation_stack[-1].family = family
            current_family = family
            if family.id:
                families_seen.add(family.id)
            continue

        if parsed.kind == "children_head":
            if parsed.inline_children and generation_stack:
                node = generation_stack[-1]
                principal = node.person
                parent_path = stack_parent_path(generation_stack)
                family_key = line_key(source_id, parent_path, parsed.text)
                family = current_family or node.family or Family.ensure_for_single_parent(
                    session,
                    source_id,
                    principal.id,
                    line_key=family_key,
                    approx=bool(principal.approx),
                )
                if family is None:
                    continue
                current_family = family
                generation_stack[-1].family = family
                if family.id:
                    families_seen.add(family.id)
                for child_text in parsed.inline_children:
                    child_clean, child_vitals = parse_vitals(child_text)
                    child_approx = vitals_are_approx(child_vitals)
                    cg, cs, _ = parse_name(child_clean, node.surname_hint)
                    if not cs and node.surname_hint:
                        cs = node.surname_hint
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
                        line_key=line_key(
                            source_id,
                            parent_path + (principal.given or "",),
                            child_clean,
                        ),
                        approx=child_approx,
                    )
                    if not child.surname and node.surname_hint:
                        child.surname = node.surname_hint
                        child.normalized_surname = Person._normalize_name(node.surname_hint)
                        session.add(child)
                    if child.id:
                        people_seen.add(child.id)
                    link = Child.link(
                        session,
                        family.id,
                        child.id,
                        line_key=line_key(source_id, parent_path, child_clean),
                        approx=child_approx,
                    )
                    if link.id:
                        children_seen.add(link.id)
                    if child_approx and family.approx is not True:
                        family.approx = True
                        session.add(family)
            continue

        if parsed.kind == "child" and generation_stack:
            node = generation_stack[-1]
            principal = node.person
            parent_path = stack_parent_path(generation_stack)
            child_clean, child_vitals = parse_vitals(parsed.text)
            child_approx = vitals_are_approx(child_vitals)
            cg, cs, _ = parse_name(child_clean, node.surname_hint)
            if not cs and node.surname_hint:
                cs = node.surname_hint
            parent_gen = principal.gen if principal.gen is not None else len(generation_stack)
            child_gen = parent_gen + 1
            if principal.gen is None:
                child_gen = token_to_generation(None, len(generation_stack))
            family_key = line_key(source_id, parent_path, "children")
            family = current_family or node.family or Family.ensure_for_single_parent(
                session,
                source_id,
                principal.id,
                line_key=family_key,
                approx=bool(principal.approx) or child_approx,
            )
            if family is None:
                continue
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
                line_key=line_key(
                    source_id,
                    parent_path + (principal.given or "",),
                    child_clean,
                ),
                approx=child_approx,
            )
            if not child.surname and node.surname_hint:
                child.surname = node.surname_hint
                child.normalized_surname = Person._normalize_name(node.surname_hint)
                session.add(child)
            if child.id:
                people_seen.add(child.id)
            generation_stack[-1].family = family
            current_family = family
            if family.id:
                families_seen.add(family.id)
            link = Child.link(
                session,
                family.id,
                child.id,
                line_key=line_key(source_id, parent_path, child_clean),
                approx=child_approx,
            )
            if link.id:
                children_seen.add(link.id)
            if child_approx and family.approx is not True:
                family.approx = True
                session.add(family)
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
