"""Smoke test for Hari 1: call Gemini via Vertex AI + verify trace appears in Phoenix."""

import sys
import os

# Allow running from repo root: python scripts/smoke_test.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.tracing.phoenix_setup import setup_phoenix_tracing
from backend.config import get_gemini_client, GEMINI_MODEL


def main() -> None:
    print("=== HonestLedger Smoke Test ===\n")

    print("[1/3] Setting up Phoenix tracing...")
    setup_phoenix_tracing()
    print("      Phoenix tracing registered.\n")

    print("[2/3] Calling Gemini via Vertex AI...")
    client = get_gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=(
            "You are an honest financial reconciliation agent. "
            "In one sentence, what does it mean for an AI agent to 'reward hack'?"
        ),
    )
    answer = response.text.strip()
    print(f"      Model : {GEMINI_MODEL}")
    print(f"      Answer: {answer}\n")

    print("[3/3] Done. Check your Phoenix Cloud dashboard for the trace.")
    print("      URL: https://app.phoenix.arize.com\n")
    print("=== Smoke test PASSED ===")


if __name__ == "__main__":
    main()
