
import csv
import json
import math
import statistics
import time
from pathlib import Path

from src.blockchain.registry import MeasurementRegistryClient


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "data" / "raw" / "dc_measurements.csv"
RESULTS_DIR = ROOT / "results"

TRIALS = 30


def percentile(values, percent):
    ordered = sorted(values)
    position = max(0, math.ceil(percent / 100 * len(ordered)) - 1)
    return ordered[position]


def main():
    with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("No measurements found.")

    payload = {
        "dataset": "dc_measurements.csv",
        "row_index": 0,
        "measurement": rows[0],
    }

    client = MeasurementRegistryClient()
    run_id = client.w3.eth.block_number
    source_timestamp = int(time.time())

    submission_ms = []
    verification_ms = []
    gas_used = []
    results = []

    for trial in range(TRIALS):
        batch_id = f"benchmark-{run_id}-{trial}"

        start = time.perf_counter()
        registered = client.record(
            batch_id,
            0,
            payload,
            source_timestamp,
        )
        submit_elapsed = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        verified = client.verify(batch_id, 0, payload)
        verify_elapsed = (time.perf_counter() - start) * 1000

        if not verified:
            raise RuntimeError(
                f"Verification failed during trial {trial}."
            )

        submission_ms.append(submit_elapsed)
        verification_ms.append(verify_elapsed)
        gas_used.append(registered["gas_used"])

        results.append({
            "trial": trial,
            "batch_id": batch_id,
            "submission_latency_ms": submit_elapsed,
            "verification_latency_ms": verify_elapsed,
            "gas_used": registered["gas_used"],
            "verified": verified,
            "transaction_hash": registered["transaction_hash"],
        })

        print(
            f"Trial {trial + 1}/{TRIALS}: "
            f"submit={submit_elapsed:.3f} ms, "
            f"verify={verify_elapsed:.3f} ms, "
            f"gas={registered['gas_used']}"
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = RESULTS_DIR / "blockchain_benchmark.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    total_submission_seconds = sum(submission_ms) / 1000

    summary = {
        "network": "Local Hardhat development chain",
        "chain_id": client.w3.eth.chain_id,
        "contract_address": client.address,
        "trials": TRIALS,
        "submission_latency_median_ms": statistics.median(submission_ms),
        "submission_latency_p95_ms": percentile(submission_ms, 95),
        "verification_latency_median_ms": statistics.median(verification_ms),
        "verification_latency_p95_ms": percentile(verification_ms, 95),
        "mean_gas_used_per_registration": statistics.mean(gas_used),
        "total_gas_used": sum(gas_used),
        "submission_throughput_per_second": (
            TRIALS / total_submission_seconds
            if total_submission_seconds else None
        ),
        "verification_success_rate": sum(
            row["verified"] for row in results
        ) / TRIALS,
    }

    summary_path = RESULTS_DIR / "blockchain_benchmark_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\n=== BLOCKCHAIN BENCHMARK SUMMARY ===")
    for key, value in summary.items():
        print(f"{key}: {value}")

    print(f"\nDetailed results: {csv_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()