
import numpy as np

from src.simulation.network import build_microgrid, run_simulation
from src.estimation.measurement_model import (
    build_dc_measurement_model,
    check_observability,
)
from src.simulation.dc_measurements import generate_dc_measurements


def test_measurement_matrix_dimensions():
    net = run_simulation(build_microgrid())
    H, measurement_info, state_bus_ids = (
        build_dc_measurement_model(net)
    )

    assert H.shape == (6, 4)
    assert len(measurement_info) == 6
    assert state_bus_ids == [1, 2, 3, 4]


def test_measurement_matrix_is_finite():
    net = run_simulation(build_microgrid())
    H, _, _ = build_dc_measurement_model(net)

    assert np.all(np.isfinite(H))


def test_network_is_observable():
    net = run_simulation(build_microgrid())
    H, _, _ = build_dc_measurement_model(net)

    result = check_observability(H)

    assert result["observable"]
    assert result["rank"] == 4
    assert result["number_of_states"] == 4


def test_measurements_are_reproducible():
    first, _, _ = generate_dc_measurements(seed=42)
    second, _, _ = generate_dc_measurements(seed=42)

    assert np.allclose(
        first["measured_flow_mw"],
        second["measured_flow_mw"],
    )


def test_zero_noise_gives_ideal_measurements():
    measurements, _, _ = generate_dc_measurements(
        seed=42,
        noise_std_mw=0.0,
    )

    assert np.allclose(
        measurements["measured_flow_mw"],
        measurements["true_flow_mw"],
    )

    assert np.allclose(measurements["noise_mw"], 0.0)


def test_measurement_matrix_matches_generated_flows():
    measurements, states, H = generate_dc_measurements(
        seed=42,
        noise_std_mw=0.0,
    )

    theta = states["reference_angle_rad"].to_numpy()
    expected_flows = H @ theta

    assert np.allclose(
        measurements["true_flow_mw"],
        expected_flows,
    )


def test_negative_noise_is_rejected():
    try:
        generate_dc_measurements(noise_std_mw=-0.01)
    except ValueError:
        pass
    else:
        raise AssertionError("Negative noise should raise ValueError.")
