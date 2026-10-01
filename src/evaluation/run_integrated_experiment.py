
from pathlib import Path
from time import perf_counter, time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.simulation.dc_measurements import generate_dc_measurements
from src.estimation.wls import estimate_states
from src.defense.residual_detector import detect_by_residual
from src.attacks.scenarios import build_attack_scenarios
from src.blockchain.registry import MeasurementRegistryClient
from src.evaluation.metrics import (
    calculate_rmse,
    binary_classification_metrics,
)

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"

NUMBER_OF_TRIALS = 100
NOISE_STD_MW = 0.01
ATTACK_MAGNITUDE_MW = 0.1
ALPHA = 0.05


def build_payload(seed, measurements):
    """Create a deterministic payload for an entire measurement batch."""
    return {
        "dataset": "synthetic_dc_measurements",
        "seed": int(seed),
        "measurement_count": int(len(measurements)),
        "measurements_mw": [
            float(format(float(value), ".12g"))
            for value in measurements
        ],
    }


def evaluate_residual_detector(H, z, theta_true, variances):
    """Run WLS and the residual detector for one measurement vector."""
    start = perf_counter()

    theta_hat = estimate_states(H, z, variances)
    detection = detect_by_residual(
        H, z, theta_hat, variances, alpha=ALPHA
    )

    elapsed_ms = (perf_counter() - start) * 1000.0

    return {
        "residual_detected": bool(detection["detected"]),
        "residual_statistic": float(detection["statistic"]),
        "residual_threshold": float(detection["threshold"]),
        "state_rmse_rad": calculate_rmse(theta_true, theta_hat),
        "residual_latency_ms": elapsed_ms,
    }


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Confirm the existing local contract is available.
    client = MeasurementRegistryClient()

    print("=== PHASE 4: INTEGRATED FDIA EXPERIMENT ===")
    print(f"Chain ID: {client.w3.eth.chain_id}")
    print(f"Contract: {client.address}")
    print(f"Trials: {NUMBER_OF_TRIALS}")

    records = []
    blockchain_submission_ms = []
    blockchain_verification_ms = []

    for seed in range(NUMBER_OF_TRIALS):
        measurements, reference, H = generate_dc_measurements(
            seed=seed,
            noise_std_mw=NOISE_STD_MW,
        )

        z_clean = measurements["measured_flow_mw"].to_numpy(
            dtype=float
        )
        theta_true = reference["reference_angle_rad"].to_numpy(
            dtype=float
        )
        variances = np.full(H.shape[0], NOISE_STD_MW**2)

        # Register the clean batch first. This is the trusted
        # reference for the post-registration tampering experiment.
        clean_payload = build_payload(seed, z_clean)
        clean_batch_id = f"phase4-clean-anchor-{seed:04d}"

        start = perf_counter()
        client.record(
            clean_batch_id,
            0,
            clean_payload,
            int(time()),
        )
        blockchain_submission_ms.append(
            (perf_counter() - start) * 1000.0
        )

        start = perf_counter()
        clean_anchor_verified = client.verify(
            clean_batch_id, 0, clean_payload
        )
        blockchain_verification_ms.append(
            (perf_counter() - start) * 1000.0
        )

        if not clean_anchor_verified:
            raise RuntimeError(
                f"Clean anchor verification failed for seed {seed}."
            )

        cases = {
            "clean": {
                "measurements": z_clean,
                "actual_attack": False,
                "attack_indices": [],
            }
        }

        attacks = build_attack_scenarios(
            H,
            z_clean,
            seed=seed + 1000,
            magnitude_mw=ATTACK_MAGNITUDE_MW,
        )

        for name, attack in attacks.items():
            cases[name] = {
                "measurements": np.asarray(
                    attack["measurements"], dtype=float
                ),
                "actual_attack": True,
                "attack_indices": attack["indices"],
            }

        for scenario_name, case in cases.items():
            z_case = case["measurements"]
            payload = build_payload(seed, z_case)

            # Check the case against the previously registered
            # clean batch. A mismatch indicates a payload change
            # relative to the clean anchor.
            start = perf_counter()
            matches_clean_anchor = client.verify(
                clean_batch_id, 0, payload
            )
            blockchain_verification_ms.append(
                (perf_counter() - start) * 1000.0
            )

            residual_result = evaluate_residual_detector(
                H, z_case, theta_true, variances
            )

            # Combined decision applies to the post-registration
            # tampering model only.
            combined_post_detected = (
                residual_result["residual_detected"]
                or not matches_clean_anchor
            )

            # A separate experiment: register each attacked batch
            # before attempting verification. This demonstrates
            # that a hash cannot establish physical truth.
            pre_registered_attack_verified = np.nan
            clean_payload_rejected_by_attack_anchor = np.nan

            if case["actual_attack"]:
                attack_batch_id = (
                    f"phase4-attacked-first-{scenario_name}-{seed:04d}"
                )

                start = perf_counter()
                client.record(
                    attack_batch_id,
                    0,
                    payload,
                    int(time()),
                )
                blockchain_submission_ms.append(
                    (perf_counter() - start) * 1000.0
                )

                start = perf_counter()
                pre_registered_attack_verified = client.verify(
                    attack_batch_id, 0, payload
                )
                blockchain_verification_ms.append(
                    (perf_counter() - start) * 1000.0
                )

                start = perf_counter()
                clean_payload_rejected_by_attack_anchor = not client.verify(
                    attack_batch_id, 0, clean_payload
                )
                blockchain_verification_ms.append(
                    (perf_counter() - start) * 1000.0
                )

            records.append({
                "seed": seed,
                "scenario": scenario_name,
                "actual_attack": case["actual_attack"],
                "attack_indices": ",".join(
                    str(i) for i in case["attack_indices"]
                ),
                "residual_detected": residual_result[
                    "residual_detected"
                ],
                "residual_statistic": residual_result[
                    "residual_statistic"
                ],
                "residual_threshold": residual_result[
                    "residual_threshold"
                ],
                "state_rmse_rad": residual_result["state_rmse_rad"],
                "residual_latency_ms": residual_result[
                    "residual_latency_ms"
                ],
                "matches_clean_anchor": bool(matches_clean_anchor),
                "blockchain_post_tamper_detected": (
                    not matches_clean_anchor
                ),
                "combined_post_tamper_detected": (
                    combined_post_detected
                ),
                "pre_registered_attack_verified": (
                    pre_registered_attack_verified
                ),
                "clean_payload_rejected_by_attack_anchor": (
                    clean_payload_rejected_by_attack_anchor
                ),
            })

        if (seed + 1) % 10 == 0:
            print(f"Completed {seed + 1}/{NUMBER_OF_TRIALS} trials")

    trials = pd.DataFrame(records)
    trials_path = RESULTS_DIR / "integrated_trials.csv"
    trials.to_csv(trials_path, index=False)

    # Summarize the residual detector and post-registration
    # integrity checks separately.
    summary_rows = []

    for scenario_name, group in trials.groupby("scenario", sort=False):
        is_clean = not bool(group["actual_attack"].any())

        summary_rows.append({
            "scenario": scenario_name,
            "trials": len(group),
            "mean_state_rmse_rad": group["state_rmse_rad"].mean(),
            "residual_detection_rate": (
                np.nan if is_clean
                else group["residual_detected"].mean()
            ),
            "residual_false_positive_rate": (
                group["residual_detected"].mean()
                if is_clean else np.nan
            ),
            "blockchain_post_tamper_detection_rate": (
                group["blockchain_post_tamper_detected"].mean()
                if not is_clean else np.nan
            ),
            "blockchain_clean_false_alarm_rate": (
                group["blockchain_post_tamper_detected"].mean()
                if is_clean else np.nan
            ),
            "combined_post_tamper_detection_rate": (
                np.nan if is_clean
                else group["combined_post_tamper_detected"].mean()
            ),
            "combined_clean_false_alarm_rate": (
                group["combined_post_tamper_detected"].mean()
                if is_clean else np.nan
            ),
            "pre_registered_attack_hash_acceptance_rate": (
                group["pre_registered_attack_verified"].mean()
                if not is_clean else np.nan
            ),
            "clean_payload_rejection_rate_after_attack_registration": (
                group["clean_payload_rejected_by_attack_anchor"].mean()
                if not is_clean else np.nan
            ),
        })

    summary = pd.DataFrame(summary_rows)
    summary_path = RESULTS_DIR / "integrated_summary.csv"
    summary.to_csv(summary_path, index=False)

    # Overall classification metrics for the residual detector.
    residual_metrics = binary_classification_metrics(
        trials["actual_attack"].to_numpy(dtype=bool),
        trials["residual_detected"].to_numpy(dtype=bool),
    )

    pd.DataFrame([residual_metrics]).to_csv(
        RESULTS_DIR / "integrated_residual_metrics.csv",
        index=False,
    )

    # Plot attack detection rates by method. The clean row is
    # excluded from detection-rate bars and reported via FPR.
    attack_summary = summary[
        summary["scenario"] != "clean"
    ]

    x = np.arange(len(attack_summary))
    width = 0.25

    plt.figure(figsize=(10, 6))
    plt.bar(
        x - width,
        attack_summary["residual_detection_rate"],
        width,
        label="WLS residual detector",
    )
    plt.bar(
        x,
        attack_summary["blockchain_post_tamper_detection_rate"],
        width,
        label="Blockchain vs clean anchor",
    )
    plt.bar(
        x + width,
        attack_summary["combined_post_tamper_detection_rate"],
        width,
        label="Combined, post-registration model",
    )

    plt.xticks(x, attack_summary["scenario"], rotation=15)
    plt.ylim(0, 1.05)
    plt.ylabel("Detection rate")
    plt.title("Phase 4: Integrated FDIA Detection")
    plt.legend()
    plt.tight_layout()
    plot_path = RESULTS_DIR / "integrated_detection_comparison.png"
    plt.savefig(plot_path, dpi=150)
    plt.close()

    print("\n=== INTEGRATED SCENARIO SUMMARY ===")
    print(summary.to_string(index=False))

    print("\n=== RESIDUAL DETECTOR OVERALL METRICS ===")
    print(pd.DataFrame([residual_metrics]).to_string(index=False))

    if not trials["pre_registered_attack_verified"].dropna().all():
        raise RuntimeError(
            "At least one pre-registered attacked payload failed "
            "its own hash verification."
        )

    if not trials[
        "clean_payload_rejected_by_attack_anchor"
    ].dropna().all():
        raise RuntimeError(
            "A clean payload unexpectedly matched an attacked anchor."
        )

    print("\n=== BLOCKCHAIN LATENCY (LOCAL HARDHAT ONLY) ===")
    print(
        "Submission median: "
        f"{np.median(blockchain_submission_ms):.3f} ms"
    )
    print(
        "Submission P95: "
        f"{np.percentile(blockchain_submission_ms, 95):.3f} ms"
    )
    print(
        "Verification median: "
        f"{np.median(blockchain_verification_ms):.3f} ms"
    )
    print(
        "Verification P95: "
        f"{np.percentile(blockchain_verification_ms, 95):.3f} ms"
    )

    print("\nSaved results:")
    print(trials_path)
    print(summary_path)
    print(RESULTS_DIR / "integrated_residual_metrics.csv")
    print(plot_path)
    print("\nPASS: integrated experiment completed.")


if __name__ == "__main__":
    main()