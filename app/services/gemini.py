"""Google Gemini (Vertex AI) client for generating the explanation.

Authentication uses GCP roles via Application Default Credentials (ADC); the
Vertex AI client only needs the project id and a location.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.config import Settings


class GeminiError(Exception):
    """Raised when the Gemini call cannot be made or returns no content."""


@lru_cache
def _client(project: str, location: str):
    """Return a cached Vertex AI Gemini client.

    The SDK is imported lazily so importing this module (and the API routes)
    does not require google-genai to be installed -- useful for tests.
    """
    from google import genai

    return genai.Client(vertexai=True, project=project, location=location)


def build_prompt(base_prompt: str, language: str, evidence: Any) -> str:
    """Assemble the final prompt text sent to Gemini.

    The base prompt ends by asking for the output language as an ISO 639 code,
    so the code is appended immediately after it; the processed evidence JSON
    follows as the data to explain.
    """
    evidence_json = json.dumps(evidence, ensure_ascii=False, indent=2)
    return (
        f"{base_prompt.rstrip()} {language}\n\n"
        f"Here is the JSON evidence to explain:\n\n{evidence_json}"
    )


def generate_explanation(
    *,
    settings: Settings,
    base_prompt: str,
    language: str,
    evidence: Any,
) -> str:
    """Generate a plain-text explanation of the evidence via Gemini.

    Note: this is a synchronous (blocking) call -- run it in a worker thread
    from async request handlers.
    """
    if not settings.gcp_project_id:
        raise GeminiError("GCP_PROJECT_ID is not configured; cannot call Gemini via Vertex AI.")

    from google.genai import types

    client = _client(settings.gcp_project_id, settings.gcp_location)
    prompt = build_prompt(base_prompt, language, evidence)

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=settings.gemini_temperature),
        )
    except Exception as exc:  # noqa: BLE001 - surface any SDK/transport error uniformly
        raise GeminiError(f"Gemini request failed: {exc}") from exc

    text = response.text
    if not text or not text.strip():
        raise GeminiError("Gemini returned an empty response.")
    return text.strip()
