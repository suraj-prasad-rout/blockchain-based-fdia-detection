
import numpy as np
import pytest

from src.estimation.wls import estimate_states
from src.estimation.residuals import calculate_residuals
from src.defense.residual_detector import detect_by_residual
from src.evaluation.metrics import (
    calculate_rmse,
    binary_classification_metrics,
)
from src.attacks.fdia import (
    random_attack,
    targeted_attack,
    model_consistent_attack,
)


def make_test_model():
    H = np.array([
        [1.0, 0.0],
        [0.0, 1.0],
        [1.0, 1.0],
        [1.0, -1.0],
    ])
    theta = np.array([0.2, -0.1])
    z = H @ theta
    variances = np.full(4, 0.01**2)
    return H, theta, z, variances


def test_wls_recovers_noiseless_states():
    H, theta, z, variances = make_test_model()
    estimate = estimate_states(H, z, variances)
    assert np.allclose(estimate, theta)


def test_wls_handles_noisy_measurements():
    H, theta, z, variances = make_test_model()
    noisy_z = z + np.array([0.001, -0.002, 0.001, 0.0])
    estimate = estimate_states(H, noisy_z, variances)
    assert np.all(np.isfinite(estimate))
    assert np.linalg.norm(estimate - theta) < 0.01


def test_wls_rejects_unobservable_model():
    H = np.array([[1.0, 0.0], [2.0, 0.0]])
    with pytest.raises(ValueError, match="unobservable"):
        estimate_states(H, np.array([1.0, 2.0]))


def test_wls_rejects_invalid_variances():
    H, _, z, _ = make_test_model()
    with pytest.raises(ValueError, match="Variances"):
        estimate_states(H, z, np.array([1.0, 0.0, 1.0, 1.0]))


def test_residuals_for_exact_measurements_are_zero():
    H, theta, z, variances = make_test_model()
    residuals, statistic = calculate_residuals(
        H, z, theta, variances
    )
    assert np.allclose(residuals, 0.0)
    assert statistic == pytest.approx(0.0)


def test_random_attack_changes_only_selected_measurements():
    _, _, z, _ = make_test_model()
    attacked, indices = random_attack(
        z, np.random.default_rng(10), 0.1, 2
    )
    changed = np.flatnonzero(~np.isclose(attacked, z))
    assert set(changed) == set(indices)
    assert len(changed) == 2
    assert np.allclose(z, make_test_model()[2])


def test_targeted_attack_changes_selected_measurements():
    _, _, z, _ = make_test_model()
    attacked, indices = targeted_attack(z, [1, 3], 0.1)
    assert np.allclose(attacked[[1, 3]], z[[1, 3]] + 0.1)
    assert np.allclose(attacked[[0, 2]], z[[0, 2]])


def test_model_consistent_attack_preserves_residual():
    H, theta, z, variances = make_test_model()
    perturbation = np.array([0.05, -0.02])

    clean_estimate = estimate_states(H, z, variances)
    attacked_z = model_consistent_attack(H, z, perturbation)
    attacked_estimate = estimate_states(H, attacked_z, variances)

    clean_residual, _ = calculate_residuals(
        H, z, clean_estimate, variances
    )
    attacked_residual, _ = calculate_residuals(
        H, attacked_z, attacked_estimate, variances
    )

    assert np.allclose(attacked_estimate, clean_estimate + perturbation)
    assert np.allclose(attacked_residual, clean_residual)


def test_rmse():
    assert calculate_rmse([1, 2], [1, 4]) == pytest.approx(
        np.sqrt(2)
    )


def test_binary_metrics():
    result = binary_classification_metrics(
        [False, False, True, True],
        [False, True, True, False],
    )
    assert result["tp"] == 1
    assert result["tn"] == 1
    assert result["fp"] == 1
    assert result["fn"] == 1
    assert result["precision"] == pytest.approx(0.5)
    assert result["recall"] == pytest.approx(0.5)
    assert result["f1"] == pytest.approx(0.5)
    assert result["false_positive_rate"] == pytest.approx(0.5)


def test_detector_rejects_invalid_alpha():
    H, theta, z, variances = make_test_model()
    with pytest.raises(ValueError, match="alpha"):
        detect_by_residual(H, z, theta, variances, alpha=1.0)
