#!/usr/bin/env python3
"""List available OpenRouter models."""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

api_key = os.getenv("GENEALOGY_OPENROUTER_API_KEY")
if not api_key:
    print("ERROR: GENEALOGY_OPENROUTER_API_KEY not set")
    sys.exit(1)

client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
)

print("Fetching available models from OpenRouter...")
print("=" * 80)

try:
    # Get list of models
    models = client.models.list()

    # Filter for free models and sort by ID
    free_models = []
    vision_models = []

    for model in models.data:
        model_id = model.id

        # Check if it's free (has :free suffix or pricing is 0)
        is_free = ':free' in model_id.lower()

        # Check if it supports vision (has "vision" in name or description)
        is_vision = 'vision' in model_id.lower() or 'vl' in model_id.lower()

        if is_free:
            free_models.append(model_id)
            if is_vision:
                vision_models.append(model_id)

    print(f"\nFREE TEXT MODELS ({len(free_models)}):")
    print("-" * 80)
    for model in sorted(free_models):
        if model not in vision_models:
            print(f"  - {model}")

    print(f"\nFREE VISION MODELS ({len(vision_models)}):")
    print("-" * 80)
    for model in sorted(vision_models):
        print(f"  - {model}")

    print("\n" + "=" * 80)
    print("RECOMMENDED configuration for free models:")
    print("=" * 80)
    if vision_models:
        print(f"GENEALOGY_OPENROUTER_OCR_MODEL={vision_models[0]}")
    if free_models:
        # Prefer non-vision models for parsing (cheaper/faster)
        text_models = [m for m in free_models if m not in vision_models]
        if text_models:
            print(f"GENEALOGY_OPENROUTER_PARSE_MODEL={text_models[0]}")
        else:
            print(f"GENEALOGY_OPENROUTER_PARSE_MODEL={free_models[0]}")

except Exception as e:
    print(f"[ERROR] Error fetching models: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
