
from pathlib import Path

import numpy as np
import pandas as pd

from src.simulation.network import (
    build_microgrid,
    run_simulation,
)


def generate_measurements(seed=42, noise_std=0.002):
    """
    Generate noisy bus-voltage measurements.

    noise_std is in per-unit voltage.
    This is a simplified sensor model.
    """
    net = run_simulation(build_microgrid())

    rng = np.random.default_rng(seed)

    true_voltage = net.res_bus["vm_pu"].to_numpy()
    noise = rng.normal(
        loc=0.0,
        scale=noise_std,
        size=len(true_voltage),
    )

    measured_voltage = true_voltage + noise

    data = pd.DataFrame({
        "bus_id": net.bus.index,
        "true_voltage_pu": true_voltage,
        "measured_voltage_pu": measured_voltage,
        "noise_pu": noise,
    })

    return data


if __name__ == "__main__":
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    data = generate_measurements()

    output_path = output_dir / "voltage_measurements.csv"
    data.to_csv(output_path, index=False)

    print(data.to_string(index=False))
    print(f"\nSaved dataset to: {output_path}")
