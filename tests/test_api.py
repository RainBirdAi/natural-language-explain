"""End-to-end tests for the /explain route.

Rainbird and Gemini are stubbed so the pipeline (fetch -> process -> explain)
is exercised without any network or GCP credentials.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services import gemini, rainbird


@pytest.fixture
def api(example_evidence, monkeypatch):
    """A TestClient with Rainbird + Gemini stubbed; yields (client, captured)."""
    captured: dict[str, Any] = {}

    async def fake_fetch(**kwargs):
        captured["fetch_kwargs"] = kwargs
        return example_evidence

    def fake_generate(*, settings, base_prompt, language, evidence):
        captured["base_prompt"] = base_prompt
        captured["language"] = language
        captured["evidence"] = evidence
        return "A concise, plain-text explanation."

    monkeypatch.setattr(rainbird, "fetch_evidence", fake_fetch)
    monkeypatch.setattr(gemini, "generate_explanation", fake_generate)

    app.dependency_overrides[get_settings] = lambda: Settings(
        gcp_project_id="test-project",
        rainbird_api_url="https://rainbird.test",
    )
    try:
        yield TestClient(app), captured
    finally:
        app.dependency_overrides.clear()


def test_explain_happy_path(api):
    client, captured = api

    resp = client.post("/explain", json={"fact_id": "F1", "session_id": "S1"})

    assert resp.status_code == 200
    # processed_evidence is omitted entirely (not null) on a non-debug request.
    assert resp.json() == {
        "explanation": "A concise, plain-text explanation.",
        "language": "en",
    }

    # Rainbird received the request inputs + configured base URL; no key sent.
    assert captured["fetch_kwargs"]["base_url"] == "https://rainbird.test"
    assert captured["fetch_kwargs"]["fact_id"] == "F1"
    assert captured["fetch_kwargs"]["session_id"] == "S1"
    assert captured["fetch_kwargs"]["evidence_key"] is None

    # Gemini received processed (date-normalised) evidence + default language.
    assert captured["language"] == "en"
    assert captured["evidence"]["time"] == "17-11-2026"
    # The ISO code is appended to the end of the base prompt.
    assert captured["base_prompt"]


def test_explain_debug_returns_processed_evidence_and_honours_overrides(api):
    client, captured = api

    resp = client.post(
        "/explain?debug=true",
        json={"fact_id": "F1", "session_id": "S1", "evidence_key": "k", "language": "de"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["language"] == "de"
    assert body["processed_evidence"]["time"] == "17-11-2026"
    assert captured["fetch_kwargs"]["evidence_key"] == "k"


@pytest.mark.parametrize(
    "payload",
    [
        {"session_id": "S1"},  # missing fact_id
        {"fact_id": "F1"},  # missing session_id
        {"fact_id": "", "session_id": "S1"},  # empty fact_id
        {"fact_id": "F1", "session_id": ""},  # empty session_id
    ],
)
def test_explain_requires_fact_and_session(api, payload):
    client, _ = api
    assert client.post("/explain", json=payload).status_code == 422


def test_explain_500_when_rainbird_url_unconfigured(monkeypatch):
    app.dependency_overrides[get_settings] = lambda: Settings(
        gcp_project_id="test-project",
        rainbird_api_url=None,
    )
    try:
        client = TestClient(app)
        resp = client.post("/explain", json={"fact_id": "F1", "session_id": "S1"})
        assert resp.status_code == 500
        assert "RAINBIRD_API_URL" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_healthz():
    assert TestClient(app).get("/healthz").json() == {"status": "ok"}
