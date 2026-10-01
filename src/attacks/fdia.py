
import numpy as np


def random_attack(z, rng, magnitude_mw=0.1, number_of_measurements=2):
    """Add random offsets to selected measurements."""
    z_attacked = np.asarray(z, dtype=float).copy()

    if magnitude_mw <= 0:
        raise ValueError("Attack magnitude must be positive.")

    if not 1 <= number_of_measurements <= len(z_attacked):
        raise ValueError("Invalid number of measurements to attack.")

    indices = rng.choice(
        len(z_attacked),
        size=number_of_measurements,
        replace=False,
    )

    offsets = rng.choice([-1.0, 1.0], size=number_of_measurements)
    z_attacked[indices] += magnitude_mw * offsets

    return z_attacked, indices


def targeted_attack(z, measurement_indices, magnitude_mw=0.1):
    """Add a fixed offset to specified measurement indices."""
    z_attacked = np.asarray(z, dtype=float).copy()
    indices = np.asarray(measurement_indices, dtype=int)

    if magnitude_mw <= 0:
        raise ValueError("Attack magnitude must be positive.")

    if indices.size == 0:
        raise ValueError("At least one measurement index is required.")

    if np.any(indices < 0) or np.any(indices >= len(z_attacked)):
        raise ValueError("Measurement index out of range.")

    z_attacked[indices] += magnitude_mw

    return z_attacked, indices


def model_consistent_attack(H, z, state_perturbation):
    """
    Construct a model-consistent linear FDIA:
        z_attack = z + H @ c

    The ideal linear residual is unchanged by this attack, while
    the estimated state shifts by c.
    """
    H = np.asarray(H, dtype=float)
    z_attacked = np.asarray(z, dtype=float).copy()
    c = np.asarray(state_perturbation, dtype=float).reshape(-1)

    if H.shape[1] != len(c):
        raise ValueError("Perturbation length must match state dimension.")

    if not np.all(np.isfinite(c)):
        raise ValueError("State perturbation must be finite.")

    z_attacked += H @ c

    return z_attacked
