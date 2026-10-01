
import json
from pathlib import Path

from web3 import Web3

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = (
    ROOT
    / "artifacts"
    / "contracts"
    / "MeasurementRegistry.sol"
    / "MeasurementRegistry.json"
)
OUTPUT_DIR = ROOT / "artifacts"
ADDRESS_PATH = OUTPUT_DIR / "contract_address.json"
ABI_PATH = OUTPUT_DIR / "contract_abi.json"

RPC_URL = "http://127.0.0.1:8545"


def main():
    if not ARTIFACT_PATH.exists():
        raise FileNotFoundError(
            f"Contract artifact not found: {ARTIFACT_PATH}\n"
            "Run: npx hardhat compile"
        )

    w3 = Web3(Web3.HTTPProvider(RPC_URL))

    if not w3.is_connected():
        raise ConnectionError(
            f"Cannot connect to Hardhat at {RPC_URL}. "
            "Make sure 'npx hardhat node' is running."
        )

    chain_id = w3.eth.chain_id
    accounts = w3.eth.accounts

    if not accounts:
        raise RuntimeError("Hardhat returned no unlocked accounts.")

    deployer = accounts[0]

    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    abi = artifact["abi"]
    bytecode = artifact["bytecode"]

    if isinstance(bytecode, dict):
        bytecode = bytecode.get("object", "")

    if not bytecode:
        raise ValueError("Contract bytecode is empty.")

    if not bytecode.startswith("0x"):
        bytecode = "0x" + bytecode

    contract_factory = w3.eth.contract(
        abi=abi,
        bytecode=bytecode,
    )

    print(f"RPC: {RPC_URL}")
    print(f"Chain ID: {chain_id}")
    print(f"Deployer: {deployer}")
    print("Deploying MeasurementRegistry...")

    tx_hash = contract_factory.constructor().transact(
        {"from": deployer}
    )
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if receipt.status != 1:
        raise RuntimeError("Contract deployment transaction failed.")

    address = receipt.contractAddress

    if not address:
        raise RuntimeError("Deployment returned no contract address.")

    contract = w3.eth.contract(address=address, abi=abi)

    owner = contract.functions.owner().call()
    authorized = contract.functions.authorizedWriters(
        deployer
    ).call()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ABI_PATH.write_text(
        json.dumps(abi, indent=2),
        encoding="utf-8",
    )

    ADDRESS_PATH.write_text(
        json.dumps(
            {
                "contract_address": address,
                "chain_id": chain_id,
                "rpc_url": RPC_URL,
                "deployer": deployer,
                "deployment_tx": tx_hash.hex(),
                "deployment_block": receipt.blockNumber,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n=== DEPLOYMENT SUCCESSFUL ===")
    print(f"Contract address: {address}")
    print(f"Owner: {owner}")
    print(f"Deployer authorized: {authorized}")
    print(f"Deployment transaction: {tx_hash.hex()}")
    print(f"Deployment block: {receipt.blockNumber}")
    print(f"ABI saved to: {ABI_PATH}")
    print(f"Address saved to: {ADDRESS_PATH}")


if __name__ == "__main__":
    main()