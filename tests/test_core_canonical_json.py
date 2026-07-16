"""Canonical JSON + hashing (register #41)."""

import hashlib

import pytest

import canonical_json


def test_hash_is_of_exactly_the_written_bytes() -> None:
    obj = {"b": 1, "a": 2}
    data = canonical_json.canonical_bytes(obj)
    assert canonical_json.sha256_of_obj(obj) == hashlib.sha256(data).hexdigest()


def test_key_order_is_irrelevant_to_output() -> None:
    assert canonical_json.canonical_bytes({"a": 1, "b": 2}) == canonical_json.canonical_bytes(
        {"b": 2, "a": 1}
    )


def test_pinned_form_compact_utf8_trailing_newline() -> None:
    data = canonical_json.canonical_bytes({"k": "café", "n": 1})
    assert data.endswith(b"\n")
    assert b", " not in data and b": " not in data  # compact separators
    assert "café".encode("utf-8") in data  # ensure_ascii=False, real UTF-8


def test_floats_are_rejected_everywhere() -> None:
    for bad in (1.0, {"x": 2.5}, [0, 1.5], {"nested": {"y": [3.0]}}):
        with pytest.raises(TypeError):
            canonical_json.canonical_bytes(bad)


def test_bool_is_allowed_not_confused_with_float() -> None:
    data = canonical_json.canonical_bytes({"flag": True, "n": 0})
    assert b"true" in data


def test_reproducible_across_calls() -> None:
    obj = {"z": [1, 2, 3], "a": {"m": "v"}}
    assert canonical_json.sha256_of_obj(obj) == canonical_json.sha256_of_obj(obj)
