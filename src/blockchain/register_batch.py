
import csv
import json
import time
from pathlib import Path

from src.blockchain.registry import MeasurementRegistryClient


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "data" / "raw" / "dc_measurements.csv"
OUTPUT_DIR = ROOT / "data" / "processed"
MANIFEST_PATH = OUTPUT_DIR / "blockchain_manifest.json"

# Use a new batch ID for a new registration run.
BATCH_ID = "microgrid-phase3-batch-001"


def read_measurements():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {CSV_PATH}")

    with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        columns = reader.fieldnames

    if not columns or not rows:
        raise ValueError("Measurement CSV has no columns or rows.")

    # Preserve all CSV fields and their values as strings.
    payloads = [
        {
            "dataset": "dc_measurements.csv",
            "row_index": index,
            "measurement": row,
        }
        for index, row in enumerate(rows)
    ]

    return payloads


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    payloads = read_measurements()
    client = MeasurementRegistryClient()

    # This is a simulation ingestion timestamp, not a sensor acquisition
    # timestamp. The CSV does not provide a confirmed acquisition time.
    source_timestamp = int(time.time())

    registrations = []

    for index, payload in enumerate(payloads):
        result = client.record(
            batch_id=BATCH_ID,
            measurement_index=index,
            payload=payload,
            source_timestamp=source_timestamp,
        )
        registrations.append(result)

        print(
            f"Registered row {index}: "
            f"tx={result['transaction_hash']}, "
            f"gas={result['gas_used']}"
        )

    manifest = {
        "batch_id": BATCH_ID,
        "dataset": str(CSV_PATH.relative_to(ROOT)),
        "payload_format": "canonical JSON; CSV values preserved as strings",
        "source_timestamp_semantics": (
            "Simulation ingestion time, not verified sensor acquisition time"
        ),
        "measurement_count": len(payloads),
        "contract_address": client.address,
        "chain_id": client.w3.eth.chain_id,
        "registrations": registrations,
    }

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print("\n=== BATCH REGISTRATION COMPLETE ===")
    print(f"Measurements registered: {len(registrations)}")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()