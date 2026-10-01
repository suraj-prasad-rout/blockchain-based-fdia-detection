
import pandapower as pp


def build_microgrid():
    """Build a small synthetic five-bus microgrid."""
    net = pp.create_empty_network(sn_mva=10.0)

    buses = [
        pp.create_bus(
            net,
            vn_kv=20.0,
            name=f"Bus {i}"
        )
        for i in range(5)
    ]

    # External grid establishes the reference voltage.
    pp.create_ext_grid(
        net,
        bus=buses[0],
        vm_pu=1.0,
        name="Grid Connection"
    )

    # Illustrative line parameters for a teaching model.
    line_params = {
        "length_km": 1.0,
        "r_ohm_per_km": 0.25,
        "x_ohm_per_km": 0.35,
        "c_nf_per_km": 10.0,
        "max_i_ka": 0.4,
    }

    connections = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),
        (0, 4),
        (1, 3),
    ]

    for start, end in connections:
        pp.create_line_from_parameters(
            net,
            from_bus=buses[start],
            to_bus=buses[end],
            **line_params
        )

    # Loads are specified in MW and MVAr.
    pp.create_load(
        net, bus=buses[2],
        p_mw=0.8, q_mvar=0.2
    )
    pp.create_load(
        net, bus=buses[3],
        p_mw=0.6, q_mvar=0.15
    )
    pp.create_load(
        net, bus=buses[4],
        p_mw=0.5, q_mvar=0.1
    )

    return net


def run_simulation(net):
    """Run AC power flow and validate convergence."""
    pp.runpp(net, algorithm="nr")

    if not net.converged:
        raise RuntimeError("Power flow did not converge")

    return net


if __name__ == "__main__":
    net = build_microgrid()
    run_simulation(net)

    print("\n=== BUS VOLTAGES ===")
    print(net.res_bus[["vm_pu", "va_degree"]])

    print("\n=== LINE RESULTS ===")
    print(
        net.res_line[
            ["p_from_mw", "p_to_mw", "loading_percent"]
        ]
    )

    print("\n=== EXTERNAL GRID ===")
    print(net.res_ext_grid[["p_mw", "q_mvar"]])
