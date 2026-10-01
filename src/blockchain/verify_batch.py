
import csv
import json
from pathlib import Path

from src.blockchain.registry import MeasurementRegistryClient


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "data" / "raw" / "dc_measurements.csv"
MANIFEST_PATH = ROOT / "data" / "processed" / "blockchain_manifest.json"
RESULT_PATH = ROOT / "results" / "blockchain_verification.csv"


def load_payloads():
    with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    return [
        {
            "dataset": "dc_measurements.csv",
            "row_index": index,
            "measurement": row,
        }
        for index, row in enumerate(rows)
    ]


def main():
    manifest = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )
    batch_id = manifest["batch_id"]
    payloads = load_payloads()

    if len(payloads) != manifest["measurement_count"]:
        raise ValueError(
            "CSV row count differs from the registered manifest."
        )

    client = MeasurementRegistryClient()
    results = []

    for index, payload in enumerate(payloads):
        valid = client.verify(batch_id, index, payload)
        record = client.get_record(batch_id, index)

        results.append({
            "batch_id": batch_id,
            "measurement_index": index,
            "verified": valid,
            "record_exists": record["exists"],
            "submitter": record["submitter"],
            "payload_hash": record["payload_hash"],
            "source_timestamp": record["source_timestamp"],
            "recorded_at": record["recorded_at"],
        })

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with RESULT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    verified_count = sum(row["verified"] for row in results)

    print("\n=== ORIGINAL MEASUREMENT VERIFICATION ===")
    print(f"Total: {len(results)}")
    print(f"Verified: {verified_count}")
    print(f"Failed: {len(results) - verified_count}")
    print(f"Results saved to: {RESULT_PATH}")

    if verified_count != len(results):
        raise RuntimeError(
            "At least one original measurement failed verification."
        )

    # Change one value in a copy of the first payload.
    # The registered original is not modified.
    if payloads:
        tampered = json.loads(json.dumps(payloads[0]))
        measurement = tampered["measurement"]

        if not measurement:
            raise ValueError("First measurement row has no fields.")

        first_key = next(iter(measurement))
        measurement[first_key] += "_TAMPERED"

        tampered_valid = client.verify(batch_id, 0, tampered)

        print("\n=== TAMPER TEST ===")
        print(f"Original row verified: {results[0]['verified']}")
        print(f"Modified row verified: {tampered_valid}")

        if tampered_valid:
            raise RuntimeError(
                "Tampering test failed: modified payload was accepted."
            )

        print("PASS: modified payload rejected.")


if __name__ == "__main__":
    main()