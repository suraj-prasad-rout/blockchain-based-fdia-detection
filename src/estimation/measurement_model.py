
import numpy as np
import pandas as pd


def build_dc_measurement_model(net, reference_bus=0):
    """
    Construct a linear DC measurement matrix from a pandapower network.

    State variables:
        Voltage phase angles (radians), excluding the reference bus.

    Measurements:
        Active-power flow on every line, in MW.

    Returns:
        H: Measurement matrix, shape (number_of_lines, number_of_states)
        measurement_info: DataFrame describing each line measurement
        state_bus_ids: Bus IDs represented in the state vector
    """
    if reference_bus not in net.bus.index:
        raise ValueError(f"Reference bus {reference_bus} does not exist.")

    if net.line.empty:
        raise ValueError("Network contains no lines.")

    # All bus angles except the reference-bus angle are unknown states.
    state_bus_ids = [
        int(bus_id)
        for bus_id in net.bus.index
        if bus_id != reference_bus
    ]

    state_column = {
        bus_id: column
        for column, bus_id in enumerate(state_bus_ids)
    }

    number_of_lines = len(net.line)
    number_of_states = len(state_bus_ids)

    H = np.zeros((number_of_lines, number_of_states))
    records = []

    # Base impedance in ohms.
    # vn_kv is line-to-line voltage; sn_mva is the network base.
    z_base_ohm = (
        net.bus.at[reference_bus, "vn_kv"] ** 2
        / net.sn_mva
    )

    for row, (line_id, line) in enumerate(net.line.iterrows()):
        from_bus = int(line["from_bus"])
        to_bus = int(line["to_bus"])

        # Total series reactance, accounting for parallel circuits.
        x_ohm = (
            line["x_ohm_per_km"]
            * line["length_km"]
            / line["parallel"]
        )

        if not np.isfinite(x_ohm) or x_ohm <= 0:
            raise ValueError(
                f"Line {line_id} has invalid reactance: {x_ohm}"
            )

        x_pu = x_ohm / z_base_ohm

        # DC approximation:
        # P_from_to (MW) = sn_mva * (theta_from - theta_to) / x_pu
        coefficient = net.sn_mva / x_pu

        if from_bus != reference_bus:
            H[row, state_column[from_bus]] += coefficient

        if to_bus != reference_bus:
            H[row, state_column[to_bus]] -= coefficient

        records.append({
            "line_id": int(line_id),
            "from_bus": from_bus,
            "to_bus": to_bus,
            "x_ohm": float(x_ohm),
            "x_pu": float(x_pu),
            "coefficient_mw_per_rad": float(coefficient),
        })

    measurement_info = pd.DataFrame(records)

    if not np.all(np.isfinite(H)):
        raise ValueError("Measurement matrix contains invalid values.")

    return H, measurement_info, state_bus_ids


def check_observability(H):
    """
    A linear state-estimation model is observable if H has
    full column rank.
    """
    rank = np.linalg.matrix_rank(H)
    number_of_states = H.shape[1]

    return {
        "rank": int(rank),
        "number_of_states": int(number_of_states),
        "observable": rank == number_of_states,
    }
