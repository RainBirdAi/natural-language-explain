"""Unit tests for the evidence post-processing (synthetic removal + dates)."""

from __future__ import annotations

from typing import Any

from app.services.evidence import (
    format_unix_timestamp,
    normalize_dates,
    process_evidence,
    strip_synthetic_facts,
)

# 1794923959928 ms -> 2026-11-17 (UTC); DOB values below are in ms too.
_TS_MILLIS = 1_794_923_959_928
_MILLIS_THRESHOLD = 1_000_000_000_000


# --- date normalisation ------------------------------------------------------


def test_format_unix_timestamp_milliseconds():
    assert format_unix_timestamp(_TS_MILLIS) == "17-11-2026"


def test_format_unix_timestamp_1990s_dob_in_ms():
    # A 12-digit ms value: must still be read as ms (1996), not seconds.
    assert format_unix_timestamp(849657600000) == "04-12-1996"


def test_normalize_time_field():
    assert normalize_dates({"time": _TS_MILLIS})["time"] == "17-11-2026"


def test_normalize_typed_value_node_datatype_date():
    # fact subject/object shape: {"value": <ms>, "dataType": "date"}
    data = {"object": {"type": "Date of Birth", "value": 849657600000, "dataType": "date"}}
    assert normalize_dates(data)["object"]["value"] == "04-12-1996"


def test_normalize_binding_date_node_type_date():
    # rule binding shape: {"type": "date", "value": <ms>}
    data = {"DEC_DATE_OF_BIRTH": {"type": "date", "value": 849657600000}}
    assert normalize_dates(data)["DEC_DATE_OF_BIRTH"]["value"] == "04-12-1996"


def test_normalize_flattened_condition_object_date():
    # flattened condition shape: {"object": <ms>, "objectType": "date"}
    data = {"object": 949449600000, "objectType": "date"}
    assert normalize_dates(data)["object"] == "02-02-2000"


def test_normalize_leaves_non_date_typed_values_untouched():
    # A string-typed value must not be converted...
    string_node = {"object": {"value": "BT17297", "dataType": "string"}}
    assert normalize_dates(string_node) == string_node
    # ...nor a boolean/truth object, nor plain numeric scores.
    assert normalize_dates({"object": True, "objectType": "truth"}) == {
        "object": True,
        "objectType": "truth",
    }
    scores = {"certainty": 100, "salience": 50, "impact": 12.5}
    assert normalize_dates(scores) == scores


def test_normalize_ignores_booleans_as_time():
    # bool is a subclass of int; it must not be treated as a timestamp.
    assert normalize_dates({"time": True}) == {"time": True}


def _max_number(data: Any) -> float:
    if isinstance(data, bool):
        return 0
    if isinstance(data, (int, float)):
        return data
    if isinstance(data, dict):
        return max((_max_number(v) for v in data.values()), default=0)
    if isinstance(data, list):
        return max((_max_number(v) for v in data), default=0)
    return 0


def test_normalize_dates_on_real_evidence(example_evidence):
    out = normalize_dates(example_evidence)

    # Top-level fact creation time.
    assert out["time"] == "17-11-2026"

    # Sanity: the raw fixture genuinely contained millisecond timestamps...
    assert _max_number(example_evidence) >= _MILLIS_THRESHOLD
    # ...and after normalisation no raw timestamp remains anywhere in the tree
    # (all remaining numbers are small scores like certainty/salience/impact).
    assert _max_number(out) < _MILLIS_THRESHOLD


def test_normalize_dates_does_not_mutate_input(example_evidence):
    original_time = example_evidence["time"]
    normalize_dates(example_evidence)
    assert example_evidence["time"] == original_time


# --- synthetic-fact removal --------------------------------------------------


def test_strip_synthetic_removes_flagged_items():
    data = {"conditions": [{"synthetic": True, "x": 1}, {"x": 2}]}
    assert strip_synthetic_facts(data) == {"conditions": [{"x": 2}]}


def test_strip_synthetic_is_noop_by_default_for_sources():
    # SYNTHETIC_SOURCES is empty by default, so nothing is dropped on `source`.
    data = {"conditions": [{"source": "injection"}, {"source": "rule"}]}
    assert strip_synthetic_facts(data) == data


def test_process_evidence_composes_both_steps():
    data = {"time": _TS_MILLIS, "conditions": [{"synthetic": True}, {"time": _TS_MILLIS}]}
    out = process_evidence(data)
    assert out["time"] == "17-11-2026"
    assert out["conditions"] == [{"time": "17-11-2026"}]
