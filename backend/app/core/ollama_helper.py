"""Ollama LLM integration for OCR correction and context-aware parsing."""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import ollama

from .settings import get_settings

LOGGER = logging.getLogger(__name__)


@dataclass
class OllamaResponse:
    """Response from Ollama API."""
    text: str
    model: str
    success: bool
    error: Optional[str] = None


@dataclass
class ParsedPerson:
    """Structured person data from LLM parsing."""
    generation: Optional[int]
    name: str
    birth_year: Optional[int]
    death_year: Optional[int]
    is_spouse: bool
    confidence: float
    birth_approx: bool = False
    death_approx: bool = False


class OllamaClient:
    """Client for interacting with local Ollama LLM."""

    def __init__(self):
        self.settings = get_settings()
        self.client = None
        if self.settings.ollama_enabled:
            try:
                # Initialize connection - store the client instance
                self.client = ollama.Client(host=self.settings.ollama_base_url)
                LOGGER.info("Ollama client initialized: %s", self.settings.ollama_base_url)
            except Exception as exc:
                LOGGER.error("Failed to initialize Ollama client: %s", exc)
                self.client = None

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        if not self.settings.ollama_enabled or not self.client:
            return False
        try:
            # Test connection
            self.client.list()
            return True
        except Exception as exc:
            LOGGER.warning("Ollama not available: %s", exc)
            return False

    def generate(self, prompt: str, model: str, format: Optional[str] = None) -> OllamaResponse:
        """Generate text using Ollama."""
        if not self.is_available():
            return OllamaResponse(
                text="",
                model=model,
                success=False,
                error="Ollama not available"
            )

        try:
            options = {
                "temperature": 0.1,  # Low temperature for consistency
                "num_predict": 512,  # Max tokens
            }

            kwargs = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": options,
            }

            if format:
                kwargs["format"] = format

            response = self.client.generate(**kwargs)

            return OllamaResponse(
                text=response.get("response", ""),
                model=model,
                success=True,
                error=None
            )
        except Exception as exc:
            LOGGER.error("Ollama generation failed: %s", exc)
            return OllamaResponse(
                text="",
                model=model,
                success=False,
                error=str(exc)
            )


# Singleton instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create the Ollama client singleton."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


# OCR Correction Prompts

def correct_ocr_text(text: str, model: Optional[str] = None) -> str:
    """
    Use LLM to correct OCR errors in genealogy text.

    Args:
        text: Raw OCR text with potential errors
        model: Model to use (defaults to ollama_ocr_model from settings)

    Returns:
        Corrected text
    """
    client = get_ollama_client()
    if not client.is_available():
        return text

    settings = get_settings()
    model = model or settings.ollama_ocr_model

    prompt = f"""You are an OCR text correction assistant specializing in genealogy documents.

The text below is from OCR of a descendancy chart. It contains OCR errors that need correction.

Common patterns in genealogy charts:
- Generation markers: "II--", "III--", "IV--" (Roman numerals followed by double dash)
- Alternative markers: "1.", "2.", "3." (Arabic numbers with period)
- Letter markers: "D--", "A--", "P--" (single letters followed by double dash)
- Spouse markers: "sp- Name" (lowercase sp followed by dash)
- Date format: "(1850-1920)" or "(b.1850 d.1920)" or "(abt 1850-1920)"
- Generation 0 means second spouse at parent level

Common OCR errors to fix:
- "D t-~" or "D *-" should be "D--"
- "sp *-" or "sp ~" should be "sp-"
- "II *-" should be "II--"
- "I l--" or "l l--" should be "II--"
- "O" mistaken for "0" in generation markers
- Broken dashes: "II -" should be "II--"

Input text:
{text}

Output ONLY the corrected text, no explanation. Preserve the original structure and line breaks."""

    response = client.generate(prompt, model)

    if response.success and response.text:
        corrected = response.text.strip()
        LOGGER.info("OCR corrected: '%s' → '%s'", text[:50], corrected[:50])
        return corrected
    else:
        LOGGER.warning("OCR correction failed: %s", response.error)
        return text


def correct_ocr_line(line: str, model: Optional[str] = None) -> str:
    """
    Correct a single line of OCR text.

    Args:
        line: Single line of OCR text
        model: Model to use (defaults to ollama_ocr_model from settings)

    Returns:
        Corrected line
    """
    client = get_ollama_client()
    if not client.is_available():
        return line

    settings = get_settings()
    model = model or settings.ollama_ocr_model

    prompt = f"""Correct OCR errors in this genealogy text line. Common patterns:
- Generation markers: "II--", "III--", "D--", "A--", "P--"
- Spouse marker: "sp-"
- Dates in parentheses: "(1850-1920)"

Fix OCR errors like:
- "D t-~" → "D--"
- "sp *-" → "sp-"
- "I l--" → "II--"

Input: {line}

Output ONLY the corrected line, no explanation."""

    response = client.generate(prompt, model)

    if response.success and response.text:
        return response.text.strip()
    else:
        return line


# Context-Aware Parsing Prompts

def parse_line_with_llm(line: str, context: Optional[Dict[str, Any]] = None, model: Optional[str] = None) -> Optional[ParsedPerson]:
    """
    Parse a genealogy line using LLM when regex parsing fails.

    Args:
        line: Text line to parse
        context: Optional context (previous generation, family info)
        model: Model to use (defaults to ollama_parse_model from settings)

    Returns:
        ParsedPerson object or None if parsing fails
    """
    client = get_ollama_client()
    if not client.is_available():
        return None

    settings = get_settings()
    model = model or settings.ollama_parse_model

    context_str = ""
    if context:
        context_str = f"\nContext:\n{json.dumps(context, indent=2)}"

    prompt = f"""You are a genealogy document parser. Extract structured information from this text line.

Line: {line}{context_str}

Extract the following information:
- generation: The generation number (1, 2, 3, etc.). Gen 0 means second spouse at parent level (treat as Gen 1).
- name: Full name of the person
- birth_year: Birth year (null if not present)
- death_year: Death year (null if not present)
- is_spouse: true if this is a spouse line (starts with "sp-"), false otherwise
- confidence: Your confidence in this parse (0.0 to 1.0)
- birth_approx: true if birth date is approximate (keywords: abt, about, circa, ca, c, ~)
- death_approx: true if death date is approximate

Common patterns:
- "II-- John Smith (1850-1920)" → generation=2, name="John Smith", birth_year=1850, death_year=1920
- "sp- Mary Jones (1855-1925)" → is_spouse=true, name="Mary Jones", birth_year=1855, death_year=1925
- "3. Jane Doe (b.1880 d.1960)" → generation=3, name="Jane Doe", birth_year=1880, death_year=1960
- "D-- Robert Brown (abt 1845-)" → generation=1, name="Robert Brown", birth_year=1845, birth_approx=true, death_year=null

Return a JSON object with these fields. If you cannot parse the line, return null."""

    response = client.generate(prompt, model, format="json")

    if not response.success:
        LOGGER.warning("LLM parsing failed: %s", response.error)
        return None

    try:
        data = json.loads(response.text)
        if not data:
            return None

        # Handle Gen 0 → Gen 1 conversion
        gen = data.get("generation")
        if gen == 0:
            gen = 1
            LOGGER.info("LLM parsed Gen 0 marker, treating as Gen 1 second spouse")

        return ParsedPerson(
            generation=gen,
            name=data.get("name", ""),
            birth_year=data.get("birth_year"),
            death_year=data.get("death_year"),
            is_spouse=data.get("is_spouse", False),
            confidence=data.get("confidence", 0.5),
            birth_approx=data.get("birth_approx", False),
            death_approx=data.get("death_approx", False),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        LOGGER.error("Failed to parse LLM response: %s", exc)
        return None


def split_multi_person_line(line: str, model: Optional[str] = None) -> List[str]:
    """
    Split a line containing multiple people into separate lines.

    Args:
        line: Text line with multiple people
        model: Model to use (defaults to ollama_parse_model from settings)

    Returns:
        List of individual person lines
    """
    client = get_ollama_client()
    if not client.is_available():
        return [line]

    settings = get_settings()
    model = model or settings.ollama_parse_model

    prompt = f"""This genealogy text line contains multiple people. Split it into separate lines, one person per line.

Input line: {line}

Preserve generation markers (II--, III--, sp-, etc.) and date formats.

Examples:
Input: "II-- John (1850-1920) sp- Mary (1855-)"
Output:
II-- John (1850-1920)
sp- Mary (1855-)

Input: "3. Jane Doe (1880-1960) 4. Bob Doe (1910-1985)"
Output:
3. Jane Doe (1880-1960)
4. Bob Doe (1910-1985)

Return each person on a separate line. If there's only one person, return the original line."""

    response = client.generate(prompt, model)

    if response.success and response.text:
        lines = [l.strip() for l in response.text.strip().split("\n") if l.strip()]
        LOGGER.info("Split line into %d parts: %s", len(lines), lines)
        return lines
    else:
        return [line]


def infer_relationship(person_name: str, parent_name: str, context: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
    """
    Use LLM to infer relationships and validate family logic.

    Args:
        person_name: Name of the person
        parent_name: Name of the parent
        context: Family context (dates, other children, etc.)
        model: Model to use (defaults to ollama_parse_model from settings)

    Returns:
        Dictionary with relationship validation results
    """
    client = get_ollama_client()
    if not client.is_available():
        return {"valid": True, "confidence": 0.5}

    settings = get_settings()
    model = model or settings.ollama_parse_model

    prompt = f"""Validate this parent-child relationship in a genealogy chart.

Person: {person_name}
Parent: {parent_name}
Context: {json.dumps(context, indent=2)}

Check for logical errors:
- Child born before parent
- Unrealistic age gaps (< 15 years or > 80 years)
- Date inconsistencies

Return JSON:
{{
  "valid": true/false,
  "confidence": 0.0-1.0,
  "issues": ["list of any issues found"],
  "suggestion": "suggested correction if invalid"
}}"""

    response = client.generate(prompt, model, format="json")

    if response.success:
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            pass

    return {"valid": True, "confidence": 0.5}
