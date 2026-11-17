"""FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="nl-explain",
    version="0.1.0",
    description=(
        "Turns a Rainbird session's evidence into a natural-language explanation: "
        "fetches evidence, removes synthetic facts, normalises dates, and asks "
        "Google Gemini to explain the reasoning in the requested language."
    ),
)

app.include_router(router)


@app.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
