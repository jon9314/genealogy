"""LLM-assisted parsing for genealogy text using context-aware analysis."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .ollama_helper import get_ollama_client, parse_line_with_llm, ParsedPerson, split_multi_person_line
from .settings import get_settings

LOGGER = logging.getLogger(__name__)


@dataclass
class LLMParseResult:
    """Result of LLM-assisted parsing."""
    success: bool
    persons: List[ParsedPerson]
    error: Optional[str] = None
    used_llm: bool = True
    fallback_reason: Optional[str] = None


class LLMParser:
    """LLM-assisted parser for ambiguous genealogy lines."""

    def __init__(self):
        self.settings = get_settings()
        self.client = get_ollama_client()
        self.stats = {
            "total_attempts": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "multi_person_splits": 0,
        }

    def is_available(self) -> bool:
        """Check if LLM parsing is available."""
        return (
            self.settings.ollama_enabled
            and self.settings.ollama_use_context_parse
            and self.client.is_available()
        )

    def parse_ambiguous_line(
        self,
        line: str,
        context: Optional[Dict[str, Any]] = None,
        reason: str = "unknown"
    ) -> LLMParseResult:
        """
        Parse an ambiguous line using LLM.

        Args:
            line: The text line to parse
            context: Optional context (generation, previous person, etc.)
            reason: Reason for using LLM (for logging/stats)

        Returns:
            LLMParseResult with parsed person(s)
        """
        self.stats["total_attempts"] += 1

        if not self.is_available():
            return LLMParseResult(
                success=False,
                persons=[],
                error="LLM not available",
                used_llm=False
            )

        LOGGER.info("LLM parsing ambiguous line (reason=%s): %s", reason, line[:80])

        # Try to split if it looks like multiple people
        if self._looks_like_multi_person(line):
            split_lines = split_multi_person_line(line, model=self.settings.ollama_parse_model)
            if len(split_lines) > 1:
                LOGGER.info("Split into %d lines", len(split_lines))
                self.stats["multi_person_splits"] += 1

                # Parse each split line
                persons = []
                for split_line in split_lines:
                    parsed = parse_line_with_llm(
                        split_line,
                        context=context,
                        model=self.settings.ollama_parse_model
                    )
                    if parsed:
                        persons.append(parsed)

                if persons:
                    self.stats["successful_parses"] += 1
                    return LLMParseResult(
                        success=True,
                        persons=persons,
                        used_llm=True,
                        fallback_reason=reason
                    )

        # Parse single line
        parsed = parse_line_with_llm(
            line,
            context=context,
            model=self.settings.ollama_parse_model
        )

        if parsed:
            self.stats["successful_parses"] += 1
            return LLMParseResult(
                success=True,
                persons=[parsed],
                used_llm=True,
                fallback_reason=reason
            )
        else:
            self.stats["failed_parses"] += 1
            return LLMParseResult(
                success=False,
                persons=[],
                error="LLM failed to parse line",
                used_llm=True,
                fallback_reason=reason
            )

    def _looks_like_multi_person(self, line: str) -> bool:
        """Check if a line likely contains multiple people."""
        import re

        # Count generation markers
        gen_markers = len(re.findall(r'\b[IVX0-9]{1,3}--', line))
        gen_markers += len(re.findall(r'\b[IVX0-9]{1,3}\.', line))

        # Count spouse markers
        spouse_markers = len(re.findall(r'\bsp-', line, re.IGNORECASE))

        # Count date patterns
        date_patterns = len(re.findall(r'\(\d{4}-\d{4}\)', line))
        date_patterns += len(re.findall(r'\(b\.\d{4}', line))

        # If multiple markers or dates, likely multi-person
        return (gen_markers + spouse_markers) > 1 or date_patterns > 1

    def parse_with_low_confidence(
        self,
        line: str,
        confidence: float,
        context: Optional[Dict[str, Any]] = None
    ) -> LLMParseResult:
        """
        Parse a line that had low OCR confidence.

        Args:
            line: The text line
            confidence: OCR confidence score (0-100)
            context: Optional parsing context

        Returns:
            LLMParseResult
        """
        threshold = self.settings.ollama_confidence_threshold * 100  # Convert to 0-100 scale

        if confidence >= threshold:
            return LLMParseResult(
                success=False,
                persons=[],
                error=f"Confidence {confidence} >= threshold {threshold}",
                used_llm=False
            )

        return self.parse_ambiguous_line(
            line,
            context=context,
            reason=f"low_confidence_{confidence:.1f}"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get parsing statistics."""
        total = self.stats["total_attempts"]
        success_rate = (
            (self.stats["successful_parses"] / total * 100)
            if total > 0
            else 0.0
        )

        return {
            **self.stats,
            "success_rate": round(success_rate, 2),
        }

    def reset_stats(self):
        """Reset parsing statistics."""
        self.stats = {
            "total_attempts": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "multi_person_splits": 0,
        }


# Singleton instance
_llm_parser: Optional[LLMParser] = None


def get_llm_parser() -> LLMParser:
    """Get or create the LLM parser singleton."""
    global _llm_parser
    if _llm_parser is None:
        _llm_parser = LLMParser()
    return _llm_parser


def parse_with_llm_fallback(
    line: str,
    regex_failed: bool = False,
    confidence: Optional[float] = None,
    context: Optional[Dict[str, Any]] = None
) -> Optional[LLMParseResult]:
    """
    Convenience function to parse with LLM fallback.

    Args:
        line: Text line to parse
        regex_failed: True if regex parsing failed
        confidence: Optional OCR confidence score
        context: Optional parsing context

    Returns:
        LLMParseResult or None if LLM not available
    """
    parser = get_llm_parser()

    if not parser.is_available():
        return None

    # Use LLM if regex failed
    if regex_failed:
        return parser.parse_ambiguous_line(
            line,
            context=context,
            reason="regex_failed"
        )

    # Use LLM if confidence is low
    if confidence is not None:
        return parser.parse_with_low_confidence(
            line,
            confidence=confidence,
            context=context
        )

    return None
