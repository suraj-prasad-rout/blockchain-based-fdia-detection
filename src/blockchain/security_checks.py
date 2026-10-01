
import csv
import json
from pathlib import Path

from src.blockchain.registry import MeasurementRegistryClient


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "data" / "raw" / "dc_measurements.csv"
MANIFEST_PATH = ROOT / "data" / "processed" / "blockchain_manifest.json"


def main():
    manifest = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )
    batch_id = manifest["batch_id"]

    with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("CSV contains no measurements.")

    payload = {
        "dataset": "dc_measurements.csv",
        "row_index": 0,
        "measurement": rows[0],
    }

    owner_client = MeasurementRegistryClient(account_index=0)
    record = owner_client.get_record(batch_id, 0)

    if not record["exists"]:
        raise RuntimeError("Register a batch before running security checks.")

    # Test 1: submit the same batch/index again.
    duplicate_rejected = False

    try:
        owner_client.record(
            batch_id,
            0,
            payload,
            record["source_timestamp"],
        )
    except Exception as exc:
        duplicate_rejected = True
        print("Duplicate submission rejected:", type(exc).__name__)

    # Test 2: account 1 is not authorized by default.
    unauthorized_rejected = False

    if owner_client.w3.eth.accounts[1] == owner_client.account:
        raise RuntimeError("Choose a different account for this test.")

    unauthorized_client = MeasurementRegistryClient(account_index=1)

    try:
        unauthorized_client.record(
            batch_id,
            0,
            payload,
            record["source_timestamp"],
        )
    except Exception as exc:
        unauthorized_rejected = True
        print("Unauthorized submission rejected:", type(exc).__name__)

    print("\n=== SECURITY CHECK RESULTS ===")
    print(f"Duplicate rejected: {duplicate_rejected}")
    print(f"Unauthorized writer rejected: {unauthorized_rejected}")

    if not duplicate_rejected or not unauthorized_rejected:
        raise RuntimeError("One or more security checks failed.")

    print("PASS: both security checks passed.")


if __name__ == "__main__":
    main()