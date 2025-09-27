from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

PERSON_RE = re.compile(r"^\s*(?:X\s*)?(?P<gen>\d+)\s*[-\u2013]{1,2}\s*(?P<body>.+)$")
SPOUSE_RE = re.compile(r"^\s*(?:X\s*)?sp\s*[-\u2013]\s*(?P<body>.+)$", re.IGNORECASE)
DATE_RE = re.compile(r"\(([^()]*)\)\s*$")
CHART_ID_RE = re.compile(r"-(\w+)$")
TITLE_TOKENS = {"LT", "LT.", "CAPT", "CAPT.", "DEACON", "REV", "REV.", "DR", "DR.", "ELD", "ELD.", "ELDER"}


@dataclass
class ParsedLine:
    gen: int
    name: str
    chart_id: Optional[str]
    birth: Optional[str]
    death: Optional[str]
    title: Optional[str]
    given: Optional[str]
    surname: Optional[str]
    is_spouse: bool
    raw: str


class ParseError(Exception):
    pass


def _extract_dates(body: str) -> tuple[str, Optional[str], Optional[str]]:
    """Return body without trailing date text plus birth/death strings."""
    birth: Optional[str] = None
    death: Optional[str] = None
    match = DATE_RE.search(body)
    if match:
        date_text = match.group(1).strip()
        body = body[: match.start()].strip()
        if date_text:
            if "-" in date_text:
                birth_part, death_part = date_text.split("-", 1)
                birth = birth_part.strip() or None
                death = death_part.strip() or None
            else:
                birth = date_text.strip() or None
    return body, birth, death


def _extract_chart_id(body: str) -> tuple[str, Optional[str]]:
    chart_id: Optional[str] = None
    match = CHART_ID_RE.search(body)
    if match:
        chart_id = match.group(1)
        body = body[: match.start()].rstrip(" -")
    return body.strip(), chart_id


def _extract_title(body: str) -> tuple[str, Optional[str]]:
    parts = body.split()
    title: Optional[str] = None
    for token in list(parts):
        cleaned = token.rstrip(".,").upper()
        if cleaned in TITLE_TOKENS:
            title = token.rstrip(",")
            parts.remove(token)
            break
    name = " ".join(parts).strip()
    return name, title


def _split_name(full_name: str) -> tuple[Optional[str], Optional[str]]:
    tokens = full_name.split()
    if not tokens:
        return None, None
    if len(tokens) == 1:
        return tokens[0], None
    given = " ".join(tokens[:-1]).strip()
    surname = tokens[-1].strip()
    return (given or None), (surname or None)


def parse_person_line(line: str) -> ParsedLine:
    match = PERSON_RE.match(line)
    if not match:
        raise ParseError(f"Line is not a person entry: {line!r}")
    gen = int(match.group("gen"))
    body = match.group("body").strip()
    body, birth, death = _extract_dates(body)
    body, chart_id = _extract_chart_id(body)
    body, title = _extract_title(body)
    name = body.strip()
    given, surname = _split_name(name)
    return ParsedLine(
        gen=gen,
        name=name,
        chart_id=chart_id,
        birth=birth,
        death=death,
        title=title,
        given=given,
        surname=surname,
        is_spouse=False,
        raw=line.strip(),
    )


def parse_spouse_line(line: str, current_gen: int) -> ParsedLine:
    match = SPOUSE_RE.match(line)
    if not match:
        raise ParseError(f"Line is not a spouse entry: {line!r}")
    body = match.group("body").strip()
    body, birth, death = _extract_dates(body)
    body, chart_id = _extract_chart_id(body)
    body, title = _extract_title(body)
    name = body.strip()
    given, surname = _split_name(name)
    return ParsedLine(
        gen=current_gen,
        name=name,
        chart_id=chart_id,
        birth=birth,
        death=death,
        title=title,
        given=given,
        surname=surname,
        is_spouse=True,
        raw=line.strip(),
    )


__all__ = [
    "ParsedLine",
    "ParseError",
    "parse_person_line",
    "parse_spouse_line",
]
