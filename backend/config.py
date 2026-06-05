"""Central config: loads env vars and initialises the Vertex AI Gemini client."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (works whether we run from root or backend/)
load_dotenv(Path(__file__).parent.parent / ".env")

GOOGLE_CLOUD_PROJECT: str = os.environ["GOOGLE_CLOUD_PROJECT"]
GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")

PHOENIX_API_KEY: str = os.environ["PHOENIX_API_KEY"]
PHOENIX_COLLECTOR_ENDPOINT: str = os.environ["PHOENIX_COLLECTOR_ENDPOINT"]


def get_gemini_client():
    """Return a google-genai Client configured for Vertex AI with explicit timeouts."""
    import google.genai as genai
    from google.genai import types

    return genai.Client(
        vertexai=True,
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION,
        http_options=types.HttpOptions(timeout=180),  # 3 min per request, not infinite
    )

