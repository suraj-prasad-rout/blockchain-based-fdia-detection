
import numpy as np

from src.attacks.fdia import (
    random_attack,
    targeted_attack,
    model_consistent_attack,
)


def build_attack_scenarios(H, z, seed=123, magnitude_mw=0.1):
    """Return named attacked measurement vectors and attack metadata."""
    rng = np.random.default_rng(seed)

    random_z, random_indices = random_attack(
        z,
        rng,
        magnitude_mw=magnitude_mw,
        number_of_measurements=2,
    )

    targeted_z, targeted_indices = targeted_attack(
        z,
        measurement_indices=[0, 4],
        magnitude_mw=magnitude_mw,
    )

    # A small angle perturbation in radians.
    perturbation = np.zeros(H.shape[1])
    perturbation[0] = 0.0002

    stealth_z = model_consistent_attack(H, z, perturbation)

    return {
        "random_attack": {
            "measurements": random_z,
            "indices": random_indices.tolist(),
        },
        "targeted_attack": {
            "measurements": targeted_z,
            "indices": targeted_indices.tolist(),
        },
        "model_consistent_attack": {
            "measurements": stealth_z,
            "indices": list(range(H.shape[0])),
        },
    }
