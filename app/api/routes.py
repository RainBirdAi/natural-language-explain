"""HTTP routes.

The /explain endpoint ties the pipeline together:
    1-2. fetch evidence from Rainbird
    3-4. strip synthetic facts + normalise dates
    5.   generate a natural-language explanation with Gemini
"""

from __future__ import annotations

import logging
import time
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.config import Settings, get_settings
from app.models import ExplainRequest, ExplainResponse
from app.services import evidence as evidence_service
from app.services import gemini, rainbird

log = logging.getLogger(__name__)

router = APIRouter()


@lru_cache
def _load_prompt(path: str) -> str:
    """Load and cache the base prompt template from disk."""
    return Path(path).read_text(encoding="utf-8")


@router.post("/explain", response_model=ExplainResponse, response_model_exclude_none=True)
async def explain(
    payload: ExplainRequest,
    debug: bool = Query(
        False,
        description="If true, also return the processed evidence (what is sent to "
        "Gemini) in the response under 'processed_evidence'.",
    ),
    settings: Settings = Depends(get_settings),
) -> ExplainResponse:
    log.info(
        "/explain request received (fact_id=%s, session_id=%s, language=%s)",
        payload.fact_id,
        payload.session_id,
        payload.language,
    )

    # Fail fast on server misconfiguration before doing any upstream work.
    if not settings.rainbird_api_url:
        raise HTTPException(
            status_code=500,
            detail="Server is not configured: RAINBIRD_API_URL is missing.",
        )
    if not settings.gcp_project_id:
        raise HTTPException(
            status_code=500,
            detail="Server is not configured: GCP_PROJECT_ID is missing.",
        )

    # 1-2. Retrieve evidence from Rainbird.
    log.info("Step 1/3: fetching evidence from Rainbird (%s)...", settings.rainbird_api_url)
    started = time.perf_counter()
    try:
        raw_evidence = await rainbird.fetch_evidence(
            base_url=settings.rainbird_api_url,
            fact_id=payload.fact_id,
            session_id=payload.session_id,
            evidence_key=payload.evidence_key,
            timeout=settings.rainbird_timeout_seconds,
        )
    except rainbird.RainbirdError as exc:
        log.warning("Rainbird request failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    log.info("Step 1/3: evidence received from Rainbird in %.2fs", time.perf_counter() - started)

    # 3-4. Remove synthetic facts and normalise unix timestamps.
    log.info("Step 2/3: processing evidence (removing synthetic facts, normalising dates)...")
    processed = evidence_service.process_evidence(raw_evidence)

    # 5. Generate the explanation via Gemini (blocking SDK -> worker thread).
    try:
        base_prompt = _load_prompt(settings.prompt_path)
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load prompt file '{settings.prompt_path}': {exc}",
        ) from exc

    log.info(
        "Step 3/3: calling Gemini (model=%s) — waiting for response, this can take a while...",
        settings.gemini_model,
    )
    started = time.perf_counter()
    try:
        explanation = await run_in_threadpool(
            gemini.generate_explanation,
            settings=settings,
            base_prompt=base_prompt,
            language=payload.language,
            evidence=processed,
        )
    except gemini.GeminiError as exc:
        log.warning("Gemini request failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    log.info(
        "Step 3/3: explanation received from Gemini in %.2fs (%d chars)",
        time.perf_counter() - started,
        len(explanation),
    )

    log.info("/explain request completed")
    return ExplainResponse(
        explanation=explanation,
        language=payload.language,
        processed_evidence=processed if debug else None,
    )
