
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.simulation.dc_measurements import generate_dc_measurements
from src.estimation.measurement_model import build_dc_measurement_model
from src.estimation.wls import estimate_states
from src.defense.residual_detector import detect_by_residual
from src.evaluation.metrics import (
    calculate_rmse,
    binary_classification_metrics,
)
from src.attacks.scenarios import build_attack_scenarios
from src.simulation.network import build_microgrid


ROOT = Path(__file__).resolve().parents[2]


def evaluate_case(
    H,
    z,
    theta_true,
    variances,
    actual_attack,
    scenario,
):
    """Estimate the state and evaluate one measurement case."""
    start = perf_counter()

    theta_hat = estimate_states(H, z, variances)
    detection = detect_by_residual(H, z, theta_hat, variances)

    elapsed_ms = (perf_counter() - start) * 1000.0

    return {
        "scenario": scenario,
        "actual_attack": bool(actual_attack),
        "detected": bool(detection["detected"]),
        "rmse_rad": calculate_rmse(theta_true, theta_hat),
        "residual_statistic": detection["statistic"],
        "threshold": detection["threshold"],
        "latency_ms": elapsed_ms,
    }


def main():
    output_dir = ROOT / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build the microgrid and its DC measurement model.
    net = build_microgrid()
    H, _, _ = build_dc_measurement_model(net)

    number_of_trials = 100
    noise_std_mw = 0.01
    attack_magnitude_mw = 0.1

    variances = np.full(
        H.shape[0],
        noise_std_mw**2,
    )

    records = []

    for seed in range(number_of_trials):
        measurements, reference, generated_H = generate_dc_measurements(
            seed=seed,
            noise_std_mw=noise_std_mw,
        )

        if not np.allclose(H, generated_H):
            raise RuntimeError(
                "Measurement model changed between trials."
            )

        z = measurements["measured_flow_mw"].to_numpy()
        theta_true = reference["reference_angle_rad"].to_numpy()

        # 1. Evaluate clean measurements.
        records.append(
            evaluate_case(
                H=H,
                z=z,
                theta_true=theta_true,
                variances=variances,
                actual_attack=False,
                scenario="clean",
            )
        )

        # 2. Generate and evaluate FDIA scenarios.
        scenarios = build_attack_scenarios(
            H,
            z,
            seed=seed + 1000,
            magnitude_mw=attack_magnitude_mw,
        )

        for scenario_name, attack_case in scenarios.items():
            records.append(
                evaluate_case(
                    H=H,
                    z=attack_case["measurements"],
                    theta_true=theta_true,
                    variances=variances,
                    actual_attack=True,
                    scenario=scenario_name,
                )
            )

    # Save every trial.
    trials = pd.DataFrame(records)

    trials.to_csv(
        output_dir / "phase2_trials.csv",
        index=False,
    )

    # 3. Calculate scenario-level summaries.
    # Detection rate is meaningful for attack scenarios.
    # False-positive rate is measured on clean scenarios.
    summary_rows = []

    for scenario_name, group in trials.groupby("scenario"):
        is_clean = not group["actual_attack"].any()

        summary_rows.append({
            "scenario": scenario_name,
            "trials": len(group),
            "mean_rmse_rad": group["rmse_rad"].mean(),
            "median_latency_ms": group["latency_ms"].median(),
            "p95_latency_ms": group["latency_ms"].quantile(0.95),
            "detection_rate": (
                np.nan if is_clean else group["detected"].mean()
            ),
            "false_positive_rate": (
                group["detected"].mean() if is_clean else np.nan
            ),
        })

    summary = pd.DataFrame(summary_rows)

    summary.to_csv(
        output_dir / "phase2_summary.csv",
        index=False,
    )

    # 4. Calculate classification metrics across all cases.
    overall_metrics = binary_classification_metrics(
        trials["actual_attack"].to_numpy(),
        trials["detected"].to_numpy(),
    )

    overall_metrics_df = pd.DataFrame([overall_metrics])

    overall_metrics_df.to_csv(
        output_dir / "phase2_overall_detection_metrics.csv",
        index=False,
    )

    # 5. Plot state-estimation RMSE by scenario.
    scenario_names = summary["scenario"].tolist()

    rmse_data = [
        trials.loc[
            trials["scenario"] == scenario_name,
            "rmse_rad",
        ].to_numpy()
        for scenario_name in scenario_names
    ]

    plt.figure()

    plt.boxplot(
        rmse_data,
        tick_labels=scenario_names,
    )

    plt.ylabel("State-estimation RMSE (radians)")
    plt.title("State-estimation error by scenario")
    plt.xticks(rotation=20)
    plt.tight_layout()

    plt.savefig(
        output_dir / "phase2_rmse.png",
        dpi=150,
    )
    plt.close()

    # 6. Plot detection rate and false-positive rate.
    plt.figure()

    x = np.arange(len(summary))
    width = 0.35

    plt.bar(
        x - width / 2,
        summary["detection_rate"].fillna(0),
        width,
        label="Detection rate",
    )

    plt.bar(
        x + width / 2,
        summary["false_positive_rate"].fillna(0),
        width,
        label="False-positive rate",
    )

    plt.xticks(x, scenario_names, rotation=20)
    plt.ylim(0, 1)
    plt.ylabel("Rate")
    plt.title("Detection and false-positive rates by scenario")
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        output_dir / "phase2_detection.png",
        dpi=150,
    )
    plt.close()

    # 7. Print the results.
    print("\n=== PHASE 2 SCENARIO SUMMARY ===")
    print(summary.to_string(index=False))

    print("\n=== OVERALL DETECTION METRICS ===")
    print(overall_metrics_df.to_string(index=False))

    print("\nSaved result files:")
    for filename in [
        "phase2_trials.csv",
        "phase2_summary.csv",
        "phase2_overall_detection_metrics.csv",
        "phase2_rmse.png",
        "phase2_detection.png",
    ]:
        print(output_dir / filename)


if __name__ == "__main__":
    main()
