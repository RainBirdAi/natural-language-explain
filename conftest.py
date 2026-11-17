"""Shared pytest fixtures.

Living at the repo root, this also ensures the root is importable so
`import app...` resolves in tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

_FIXTURES = Path(__file__).parent / "tests" / "fixtures"


@pytest.fixture
def example_evidence() -> dict[str, Any]:
    """A real evidence payload captured from the Rainbird evidence endpoint."""
    return json.loads((_FIXTURES / "example_evidence.json").read_text(encoding="utf-8"))
