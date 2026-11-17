"""Evidence post-processing: synthetic-fact removal and date normalisation.

These functions are pure and recursive -- they walk the parsed evidence JSON
(arbitrary nesting of dicts/lists) and return a new, transformed structure
without mutating the input.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# 3. Synthetic-fact removal
# ---------------------------------------------------------------------------
# TODO(project owner): The precise definition of a "synthetic fact" in Rainbird
# evidence is still to be confirmed. The traversal below is complete and tested;
# only the `is_synthetic_fact` predicate needs the real rule once we have it.
#
# Until then the default behaviour is a safe no-op (nothing is removed): the
# `synthetic: true` flag is honoured if present, and `SYNTHETIC_SOURCES` is an
# opt-in set of `source` values to treat as synthetic (empty by default, so no
# evidence is dropped by accident).
SYNTHETIC_SOURCES: set[str] = set()  # e.g. {"injection"} once confirmed


def is_synthetic_fact(node: dict[str, Any]) -> bool:
    """Return True if a dict node represents a synthetic fact to be removed."""
    if node.get("synthetic") is True:
        return True
    source = node.get("source")
    if isinstance(source, str) and source in SYNTHETIC_SOURCES:
        return True
    return False


def strip_synthetic_facts(data: Any) -> Any:
    """Recursively drop synthetic-fact items from any list in the structure."""
    if isinstance(data, dict):
        return {key: strip_synthetic_facts(value) for key, value in data.items()}
    if isinstance(data, list):
        return [
            strip_synthetic_facts(item)
            for item in data
            if not (isinstance(item, dict) and is_synthetic_fact(item))
        ]
    return data


# ---------------------------------------------------------------------------
# 4. Date normalisation (unix timestamp -> dd-mm-yyyy)
# ---------------------------------------------------------------------------
DATE_FORMAT = "%d-%m-%Y"

# The "time" key always holds a unix timestamp (fact creation time).
_TIME_KEY = "time"


def _is_timestamp(value: Any) -> bool:
    """True for a real numeric timestamp (bool is excluded -- it subclasses int)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def format_unix_timestamp(value_ms: int | float) -> str:
    """Format a Rainbird unix timestamp (epoch milliseconds, UTC) as dd-mm-yyyy.

    Rainbird reports times and date values as epoch milliseconds (the JS
    convention). A magnitude-based seconds/ms guess is deliberately avoided: it
    misclassifies older dates (e.g. a 1990s date of birth in ms sits below a
    13-digit threshold) and cannot represent pre-1970 dates at all.
    """
    return datetime.fromtimestamp(value_ms / 1000, tz=timezone.utc).strftime(DATE_FORMAT)


def normalize_dates(data: Any) -> Any:
    """Recursively convert unix timestamps to human-readable dd-mm-yyyy dates.

    Timestamps appear in the evidence in several shapes:

    * ``"time": 1794923959928`` -- fact creation time (always a timestamp).
    * a typed value node, ``{"dataType": "date", "value": <ms>}`` (fact
      subject/object) or ``{"type": "date", "value": <ms>}`` (rule binding).
    * a flattened condition, ``{"objectType": "date", "object": <ms>}``
      (and defensively the ``subject``/``subjectType`` pair).
    """
    if isinstance(data, dict):
        value_is_date = data.get("dataType") == "date" or data.get("type") == "date"
        object_is_date = data.get("objectType") == "date"
        subject_is_date = data.get("subjectType") == "date"

        result: dict[str, Any] = {}
        for key, value in data.items():
            if key == _TIME_KEY and _is_timestamp(value):
                result[key] = format_unix_timestamp(value)
            elif key == "value" and value_is_date and _is_timestamp(value):
                result[key] = format_unix_timestamp(value)
            elif key == "object" and object_is_date and _is_timestamp(value):
                result[key] = format_unix_timestamp(value)
            elif key == "subject" and subject_is_date and _is_timestamp(value):
                result[key] = format_unix_timestamp(value)
            else:
                result[key] = normalize_dates(value)
        return result
    if isinstance(data, list):
        return [normalize_dates(item) for item in data]
    return data


def process_evidence(evidence: Any) -> Any:
    """Apply synthetic-fact removal followed by date normalisation."""
    return normalize_dates(strip_synthetic_facts(evidence))
