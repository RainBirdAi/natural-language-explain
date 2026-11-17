"""Tests for the Rainbird evidence client (URL + header construction)."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.services import rainbird

BASE = "https://rb.test"
EVIDENCE_URL = f"{BASE}/analysis/evidence/F1/S1"


@respx.mock
async def test_fetch_evidence_builds_url_and_sends_key():
    route = respx.get(EVIDENCE_URL, params={"full": "true"}).mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    result = await rainbird.fetch_evidence(
        base_url=f"{BASE}/",  # trailing slash should be handled
        fact_id="F1",
        session_id="S1",
        evidence_key="secret-key",
        timeout=5,
    )

    assert result == {"ok": True}
    assert route.called
    request = route.calls.last.request
    assert request.headers["x-evidence-key"] == "secret-key"
    # full=true must be present to get the recursive evidence tree.
    assert request.url.params["full"] == "true"


@respx.mock
async def test_fetch_evidence_omits_header_when_no_key():
    route = respx.get(EVIDENCE_URL).mock(return_value=httpx.Response(200, json={}))

    await rainbird.fetch_evidence(
        base_url=BASE,
        fact_id="F1",
        session_id="S1",
        evidence_key=None,
        timeout=5,
    )

    assert "x-evidence-key" not in route.calls.last.request.headers


@respx.mock
async def test_fetch_evidence_raises_on_http_error():
    respx.get(EVIDENCE_URL).mock(return_value=httpx.Response(404, text="not found"))

    with pytest.raises(rainbird.RainbirdError):
        await rainbird.fetch_evidence(
            base_url=BASE,
            fact_id="F1",
            session_id="S1",
            evidence_key=None,
            timeout=5,
        )


@respx.mock
async def test_fetch_evidence_raises_on_bad_json():
    respx.get(EVIDENCE_URL).mock(return_value=httpx.Response(200, text="not json"))

    with pytest.raises(rainbird.RainbirdError):
        await rainbird.fetch_evidence(
            base_url=BASE,
            fact_id="F1",
            session_id="S1",
            evidence_key=None,
            timeout=5,
        )
