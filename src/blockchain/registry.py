
import json
from pathlib import Path
from typing import Any

from web3 import Web3


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "artifacts"

ABI_PATH = ARTIFACT_DIR / "contract_abi.json"
ADDRESS_PATH = ARTIFACT_DIR / "contract_address.json"

DEFAULT_RPC_URL = "http://127.0.0.1:8545"


def canonical_json(payload: dict[str, Any]) -> str:
    """Serialize a payload deterministically before hashing."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def payload_hash(payload: dict[str, Any]) -> bytes:
    """Return the Keccak-256 hash of a canonical payload."""
    return bytes(Web3.keccak(text=canonical_json(payload)))


def batch_id_hash(batch_id: str) -> bytes:
    """Convert a readable batch ID to bytes32."""
    if not batch_id.strip():
        raise ValueError("Batch ID cannot be empty.")
    return bytes(Web3.keccak(text=batch_id))


class MeasurementRegistryClient:
    def __init__(
        self,
        rpc_url: str = DEFAULT_RPC_URL,
        account_index: int = 0,
    ):
        if not ABI_PATH.exists() or not ADDRESS_PATH.exists():
            raise FileNotFoundError(
                "Contract ABI/address not found. "
                "Deploy the contract first."
            )

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError(
                f"Cannot connect to blockchain at {rpc_url}"
            )

        config = json.loads(
            ADDRESS_PATH.read_text(encoding="utf-8")
        )
        abi = json.loads(ABI_PATH.read_text(encoding="utf-8"))

        expected_chain_id = int(config["chain_id"])
        actual_chain_id = self.w3.eth.chain_id

        if actual_chain_id != expected_chain_id:
            raise RuntimeError(
                f"Chain ID mismatch: expected {expected_chain_id}, "
                f"got {actual_chain_id}. The node may have restarted; "
                "redeploy the contract."
            )

        self.address = Web3.to_checksum_address(
            config["contract_address"]
        )
        self.contract = self.w3.eth.contract(
            address=self.address,
            abi=abi,
        )

        accounts = self.w3.eth.accounts
        if account_index >= len(accounts):
            raise IndexError("Requested account index does not exist.")

        self.account = Web3.to_checksum_address(
            accounts[account_index]
        )

    def record(
        self,
        batch_id: str,
        measurement_index: int,
        payload: dict[str, Any],
        source_timestamp: int,
    ) -> dict[str, Any]:
        """Register one measurement hash on-chain."""
        if not 0 <= measurement_index <= 2**32 - 1:
            raise ValueError("Measurement index must fit uint32.")

        if not 0 < source_timestamp <= 2**64 - 1:
            raise ValueError("Timestamp must fit positive uint64.")

        batch_hash = batch_id_hash(batch_id)
        digest = payload_hash(payload)

        tx_hash = self.contract.functions.recordMeasurement(
            batch_hash,
            measurement_index,
            digest,
            source_timestamp,
        ).transact({"from": self.account})

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status != 1:
            raise RuntimeError("Measurement registration failed.")

        return {
            "batch_id": batch_id,
            "measurement_index": measurement_index,
            "payload_hash": Web3.to_hex(digest),
            "transaction_hash": receipt.transactionHash.hex(),
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "account": self.account,
        }

    def verify(
        self,
        batch_id: str,
        measurement_index: int,
        payload: dict[str, Any],
    ) -> bool:
        """Return True only when the payload matches the stored hash."""
        return self.contract.functions.verifyMeasurement(
            batch_id_hash(batch_id),
            measurement_index,
            payload_hash(payload),
        ).call()

    def get_record(
        self,
        batch_id: str,
        measurement_index: int,
    ) -> dict[str, Any]:
        """Retrieve the on-chain record."""
        result = self.contract.functions.getMeasurement(
            batch_id_hash(batch_id),
            measurement_index,
        ).call()

        digest, submitter, source_ts, recorded_at, exists = result

        return {
            "payload_hash": Web3.to_hex(digest),
            "submitter": submitter,
            "source_timestamp": source_ts,
            "recorded_at": recorded_at,
            "exists": exists,
        }

    def authorize_writer(
        self,
        writer_address: str,
        authorized: bool = True,
    ) -> dict[str, Any]:
        """Owner-only operation to grant/revoke writer permission."""
        writer_address = Web3.to_checksum_address(writer_address)

        tx_hash = self.contract.functions.setWriter(
            writer_address,
            authorized,
        ).transact({"from": self.account})

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status != 1:
            raise RuntimeError("Writer authorization failed.")

        return {
            "writer": writer_address,
            "authorized": authorized,
            "transaction_hash": receipt.transactionHash.hex(),
            "gas_used": receipt.gasUsed,
        }