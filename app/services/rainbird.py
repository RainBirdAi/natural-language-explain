"""Client for the Rainbird evidence endpoint.

Docs: https://docs.rainbird.ai/rainbird/developer-docs/api-reference/evidence

    GET {base_url}/analysis/evidence/{fact_id}/{session_id}?full=true
    header: x-evidence-key: <evidence_key>

The evidence is secured by default; access is granted via the evidence key, so
no account-level X-API-Key is required for this flow. The ``full=true`` query
parameter returns the full evidence tree, with recursive nested facts.
"""

from __future__ import annotations

from typing import Any

import httpx

EVIDENCE_PATH = "/analysis/evidence/{fact_id}/{session_id}"
# full=true returns the complete evidence tree (recursive nested facts).
EVIDENCE_QUERY = {"full": "true"}


class RainbirdError(Exception):
    """Raised when the Rainbird evidence request fails or returns bad data."""


async def fetch_evidence(
    *,
    base_url: str,
    fact_id: str,
    session_id: str,
    evidence_key: str | None,
    timeout: float,
) -> dict[str, Any]:
    """Fetch raw evidence JSON for a fact from a Rainbird session.

    ``evidence_key`` is only sent (as the ``x-evidence-key`` header) when
    provided; omit it when evidence security is disabled in Rainbird.
    """
    url = base_url.rstrip("/") + EVIDENCE_PATH.format(fact_id=fact_id, session_id=session_id)
    headers = {"Accept": "application/json"}
    if evidence_key:
        headers["x-evidence-key"] = evidence_key

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers, params=EVIDENCE_QUERY)
    except httpx.HTTPError as exc:
        raise RainbirdError(f"Could not reach Rainbird at {url}: {exc}") from exc

    if response.status_code != httpx.codes.OK:
        raise RainbirdError(
            f"Rainbird evidence request failed ({response.status_code}): "
            f"{response.text[:500]}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise RainbirdError("Rainbird evidence response was not valid JSON.") from exc
