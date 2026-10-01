
import numpy as np

from src.simulation.network import (
    build_microgrid,
    run_simulation,
)
from src.simulation.measurements import generate_measurements


def test_network_converges():
    net = run_simulation(build_microgrid())

    assert net.converged
    assert len(net.bus) == 5
    assert len(net.line) == 6


def test_voltage_results_are_finite():
    net = run_simulation(build_microgrid())

    voltages = net.res_bus["vm_pu"].to_numpy()

    assert np.all(np.isfinite(voltages))
    assert np.all(voltages > 0)


def test_measurements_are_reproducible():
    first = generate_measurements(seed=42)
    second = generate_measurements(seed=42)

    assert np.allclose(
        first["measured_voltage_pu"],
        second["measured_voltage_pu"],
    )


def test_measurement_noise_is_added():
    data = generate_measurements(seed=42)

    assert not np.allclose(
        data["true_voltage_pu"],
        data["measured_voltage_pu"],
    )
