
from pathlib import Path

import numpy as np
import pandas as pd

from src.estimation.measurement_model import (
    build_dc_measurement_model,
)
from src.estimation.wls import estimate_states
from src.evaluation.metrics import calculate_rmse
from src.simulation.network import build_microgrid


def main():
    data_path = Path("data/raw/dc_measurements.csv")
    reference_path = Path("data/raw/dc_reference_states.csv")

    if not data_path.exists() or not reference_path.exists():
        raise FileNotFoundError(
            "Run python -m src.simulation.dc_measurements first."
        )

    measurements = pd.read_csv(data_path)
    reference = pd.read_csv(reference_path)

    net = build_microgrid()
    H, _, state_bus_ids = build_dc_measurement_model(net)

    z = measurements["measured_flow_mw"].to_numpy()
    theta_true = reference["reference_angle_rad"].to_numpy()

    # Each measurement has the same assumed standard deviation of 0.01 MW.
    # Equal variances yield equal relative weights.
    noise_std_mw = 0.01
    variances = np.full(len(z), noise_std_mw**2)

    theta_hat = estimate_states(H, z, variances)
    rmse = calculate_rmse(theta_true, theta_hat)

    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = pd.DataFrame({
        "bus_id": state_bus_ids,
        "reference_angle_rad": theta_true,
        "estimated_angle_rad": theta_hat,
        "reference_angle_degree": np.rad2deg(theta_true),
        "estimated_angle_degree": np.rad2deg(theta_hat),
        "absolute_error_rad": np.abs(theta_true - theta_hat),
    })

    output_path = output_dir / "estimated_states.csv"
    results.to_csv(output_path, index=False)

    print("\n=== WLS STATE ESTIMATION ===")
    print(results.to_string(index=False))
    print(f"\nState RMSE (radians): {rmse:.8f}")
    print(f"State RMSE (degrees): {np.rad2deg(rmse):.8f}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
