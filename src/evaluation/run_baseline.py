
from pathlib import Path

import numpy as np
import pandas as pd

from src.estimation.measurement_model import build_dc_measurement_model
from src.estimation.wls import estimate_states
from src.defense.residual_detector import detect_by_residual
from src.evaluation.metrics import calculate_rmse
from src.simulation.network import build_microgrid


def main():
    measurements = pd.read_csv("data/raw/dc_measurements.csv")
    reference = pd.read_csv("data/raw/dc_reference_states.csv")

    H, _, state_bus_ids = build_dc_measurement_model(build_microgrid())
    z = measurements["measured_flow_mw"].to_numpy()
    theta_true = reference["reference_angle_rad"].to_numpy()

    # This matches the noise standard deviation used by Track 1.
    variances = np.full(len(z), 0.01**2)

    theta_hat = estimate_states(H, z, variances)
    detection = detect_by_residual(H, z, theta_hat, variances)
    rmse = calculate_rmse(theta_true, theta_hat)

    summary = pd.DataFrame([{
        "scenario": "clean_baseline",
        "rmse_rad": rmse,
        "residual_statistic": detection["statistic"],
        "threshold": detection["threshold"],
        "detected": detection["detected"],
    }])

    output_dir = Path("results")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_dir / "baseline_summary.csv", index=False)

    residual_table = pd.DataFrame({
        "line_id": measurements["line_id"],
        "residual_mw": detection["residuals"],
    })
    residual_table.to_csv(output_dir / "baseline_residuals.csv", index=False)

    print(summary.to_string(index=False))
    print(f"Saved baseline results to {output_dir}")


if __name__ == "__main__":
    main()
