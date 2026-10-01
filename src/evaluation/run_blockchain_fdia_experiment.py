import math
import csv
import json
import time
from pathlib import Path

from src.blockchain.registry import MeasurementRegistryClient


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "data" / "raw" / "dc_measurements.csv"
OUTPUT_PATH = ROOT / "results" / "blockchain_fdia_experiment.csv"


def make_payload(row):
    return {
        "dataset": "dc_measurements.csv",
        "row_index": 0,
        "measurement": row,
    }


def modify_numeric_value(payload):
    """Alter an electrical measurement, not a bus or line identifier."""
    altered = json.loads(json.dumps(payload))
    row = altered["measurement"]

    # Prefer the actual DC line-flow measurement.
    preferred_fields = [
        "measured_flow_mw",
        "measured_flow",
        "flow_mw",
        "measurement_value",
    ]

    target = next(
        (key for key in preferred_fields if key in row),
        None,
    )

    if target is None:
        raise ValueError(
            "Could not find a recognized measurement-value column. "
            f"Available columns: {list(row.keys())}"
        )

    try:
        original_value = float(row[target])
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Measurement field {target!r} is not numeric."
        ) from exc

    if not math.isfinite(original_value):
        raise ValueError("Measurement value must be finite.")

    modified_value = original_value + 0.1
    row[target] = format(modified_value, ".12g")

    return altered, target, row[target] if False else original_value, format(
        modified_value, ".12g"
    )

def main():
    with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("Measurement CSV is empty.")

    client = MeasurementRegistryClient()

    original = make_payload(rows[0])
    tampered, changed_field, original_value, changed_value = (
        modify_numeric_value(original)
    )

    # Use unique batch IDs so this experiment can be rerun on the same node.
    run_id = time.time_ns()
    timestamp = int(time.time())

    # Case A: register the original, then test the altered payload.
    batch_after = f"fdia-after-registration-{run_id}"

    client.record(batch_after, 0, original, timestamp)
    original_after = client.verify(batch_after, 0, original)
    tampered_after = client.verify(batch_after, 0, tampered)

    # Case B: register the modified payload first.
    batch_before = f"fdia-before-registration-{run_id}"

    client.record(batch_before, 0, tampered, timestamp)
    tampered_before = client.verify(batch_before, 0, tampered)
    original_before = client.verify(batch_before, 0, original)

    results = [
        {
            "case": "Modified after registration",
            "registered_payload": "original",
            "verification_of_original": original_after,
            "verification_of_tampered": tampered_after,
            "interpretation": (
                "Expected: tampered payload rejected"
            ),
        },
        {
            "case": "Modified before registration",
            "registered_payload": "tampered",
            "verification_of_original": original_before,
            "verification_of_tampered": tampered_before,
            "interpretation": (
                "Expected: registered false payload still verifies"
            ),
        },
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print("Changed field:", changed_field)
    print("Original value:", original_value)
    print("Modified value:", changed_value)
    print("\n=== BLOCKCHAIN / FDIA EXPERIMENT ===")

    for result in results:
        print(f"\n{result['case']}")
        print("  Original verifies:", result["verification_of_original"])
        print("  Tampered verifies:", result["verification_of_tampered"])

    if not original_after or tampered_after:
        raise RuntimeError("Post-registration tampering test failed.")

    if original_before or not tampered_before:
        raise RuntimeError("Pre-registration false-data test failed.")

    print("\nPASS: both expected outcomes observed.")
    print("Results saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()