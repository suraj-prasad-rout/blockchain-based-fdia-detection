import numpy as np
import pytest
from src.evaluation.run_integrated_experiment import build_payload
from src.blockchain.registry import payload_hash, canonical_json
def test_build_payload_has_expected_structure():
    payload = build_payload(7, np.array([1.25, -2.5, 0.0]))
    assert payload == {
        "dataset": "synthetic_dc_measurements",
        "seed": 7,
        "measurement_count": 3,
        "measurements_mw": [1.25, -2.5, 0.0],
    }
def test_build_payload_is_deterministic():
    measurements = np.array([1.23456789012345, -0.12345678901234])
    first = build_payload(10, measurements)
    second = build_payload(10, measurements.copy())
    assert first == second
    assert payload_hash(first) == payload_hash(second)
def test_build_payload_rounds_measurements_to_12_significant_digits():
    payload = build_payload(1, np.array([1.234567890123456]))
    assert payload["measurements_mw"] == [
        float(format(1.234567890123456, ".12g"))
    ]
def test_payload_hash_changes_when_measurement_changes():
    original = build_payload(1, np.array([1.0, 2.0]))
    modified = build_payload(1, np.array([1.0, 2.1]))
    assert payload_hash(original) != payload_hash(modified)
def test_payload_hash_is_independent_of_dictionary_key_order():
    first = {"seed": 1, "measurement_count": 1}
    second = {"measurement_count": 1, "seed": 1}
    assert canonical_json(first) == canonical_json(second)
    assert payload_hash(first) == payload_hash(second)
def test_non_finite_measurements_are_rejected_by_canonical_json():
    payload = build_payload(1, np.array([float("nan")]))
    with pytest.raises(ValueError):
        canonical_json(payload)
