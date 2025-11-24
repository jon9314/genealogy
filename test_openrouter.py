#!/usr/bin/env python3
"""Quick test script for OpenRouter integration."""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

from app.core.settings import get_settings
from app.core.ollama_helper import get_llm_client, parse_line_with_llm, correct_ocr_line


def test_openrouter_connection():
    """Test basic OpenRouter connection."""
    print("=" * 60)
    print("Testing OpenRouter Integration")
    print("=" * 60)

    # Get settings
    settings = get_settings()
    print(f"\nLLM Provider: {settings.llm_provider}")

    if settings.llm_provider == "openrouter":
        print(f"OpenRouter API Key: {'*' * 20}{settings.openrouter_api_key[-10:] if settings.openrouter_api_key else 'NOT SET'}")
        print(f"OCR Model: {settings.openrouter_ocr_model}")
        print(f"Parse Model: {settings.openrouter_parse_model}")

    # Get client
    client = get_llm_client()
    print(f"\nClient Type: {type(client).__name__}")
    print(f"Client Available: {client.is_available()}")

    if not client.is_available():
        print("\n[FAIL] Client not available! Check your configuration.")
        return False

    print("\n[OK] Client initialized successfully!")

    # Test 1: Simple OCR correction
    print("\n" + "-" * 60)
    print("Test 1: OCR Correction")
    print("-" * 60)
    test_line = "II *- John Smith (1850-1920)"
    print(f"Input:  {test_line}")
    corrected = correct_ocr_line(test_line)
    print(f"Output: {corrected}")

    # Test 2: Parse a genealogy line
    print("\n" + "-" * 60)
    print("Test 2: Parse Genealogy Line")
    print("-" * 60)
    test_line = "III-- Mary Jones (1875-1945)"
    print(f"Input: {test_line}")
    parsed = parse_line_with_llm(test_line)

    if parsed:
        print("[OK] Parsed successfully!")
        print(f"  Name: {parsed.name}")
        print(f"  Generation: {parsed.generation}")
        print(f"  Birth Year: {parsed.birth_year}")
        print(f"  Death Year: {parsed.death_year}")
        print(f"  Confidence: {parsed.confidence}")
    else:
        print("[FAIL] Failed to parse line")
        return False

    print("\n" + "=" * 60)
    print("[OK] All tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_openrouter_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
