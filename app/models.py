"""Request and response models for the HTTP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExplainRequest(BaseModel):
    """Inputs for a single explanation request."""

    fact_id: str = Field(
        ...,
        min_length=1,
        description="The Rainbird fact identifier to retrieve evidence for. Required.",
    )
    session_id: str = Field(
        ...,
        min_length=1,
        description="The Rainbird session in which the fact was created. Required.",
    )
    evidence_key: str | None = Field(
        default=None,
        description="Evidence key, sent to Rainbird as the 'x-evidence-key' header. "
        "Optional: only needed when evidence is secured in Rainbird.",
    )
    language: str = Field(
        default="en",
        description="ISO 639 language code for the explanation output, e.g. 'en', 'de', 'fr'. "
        "Defaults to 'en'.",
        examples=["en"],
    )


class ExplainResponse(BaseModel):
    """The generated explanation."""

    explanation: str = Field(..., description="Plain-text explanation produced by Gemini.")
    language: str = Field(..., description="ISO 639 language code the explanation was requested in.")
    processed_evidence: dict[str, Any] | None = Field(
        default=None,
        description="The evidence after synthetic-fact removal and date normalisation. "
        "Only populated when the request is made with ?debug=true.",
    )
