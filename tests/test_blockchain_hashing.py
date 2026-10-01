
import pytest

from src.blockchain.registry import (
    canonical_json,
    payload_hash,
    batch_id_hash,
)


def test_canonical_json_ignores_dictionary_key_order():
    first = {"bus": 2, "voltage": "1.01"}
    second = {"voltage": "1.01", "bus": 2}

    assert canonical_json(first) == canonical_json(second)
    assert payload_hash(first) == payload_hash(second)


def test_modified_payload_has_different_hash():
    original = {"bus": 2, "voltage": "1.01"}
    modified = {"bus": 2, "voltage": "1.02"}

    assert payload_hash(original) != payload_hash(modified)


def test_batch_id_hash_is_32_bytes():
    assert len(batch_id_hash("phase3-test")) == 32


def test_empty_batch_id_is_rejected():
    with pytest.raises(ValueError):
        batch_id_hash("   ")


def test_non_finite_json_values_are_rejected():
    with pytest.raises(ValueError):
        canonical_json({"value": float("nan")})