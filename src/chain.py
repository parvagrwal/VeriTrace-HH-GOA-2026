import os
import sys

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union
from hexbytes import HexBytes
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from src.pipeline import compute_canonical_record_hash

# Polygon Amoy RPC endpoints (primary and reliable fallbacks)
DEFAULT_AMOY_RPCS = [
    "https://polygon-amoy.drpc.org",
    "https://polygon-amoy-bor-rpc.publicnode.com",
    "https://rpc-amoy.polygon.technology",
]
DEFAULT_AMOY_RPC = DEFAULT_AMOY_RPCS[0]
AMOY_EXPLORER_URL = "https://amoy.polygonscan.com"

# VerificationRegistry Contract ABI
VERIFICATION_REGISTRY_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "recordHash", "type": "bytes32"}],
        "name": "storeRecord",
        "outputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
        "name": "getRecord",
        "outputs": [
            {"internalType": "bytes32", "name": "recordHash", "type": "bytes32"},
            {"internalType": "address", "name": "submitter", "type": "address"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "records",
        "outputs": [
            {"internalType": "bytes32", "name": "recordHash", "type": "bytes32"},
            {"internalType": "address", "name": "submitter", "type": "address"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "recordCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalRecords",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "id", "type": "uint256"},
            {"indexed": True, "internalType": "bytes32", "name": "recordHash", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "submitter", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "RecordStored",
        "type": "event",
    },
]


def get_web3_client(rpc_url: Optional[str] = None) -> Web3:
    endpoints_to_try = [rpc_url] if rpc_url else []
    env_rpc = os.getenv("AMOY_RPC_URL")
    if env_rpc and env_rpc not in endpoints_to_try:
        endpoints_to_try.append(env_rpc)
    for r in DEFAULT_AMOY_RPCS:
        if r not in endpoints_to_try:
            endpoints_to_try.append(r)

    for ep in endpoints_to_try:
        try:
            w3 = Web3(Web3.HTTPProvider(ep, request_kwargs={"timeout": 10}))
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            if w3.is_connected():
                return w3
        except Exception:
            continue

    fallback = Web3(Web3.HTTPProvider(DEFAULT_AMOY_RPC))
    fallback.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return fallback


def get_contract(
    w3: Optional[Web3] = None,
    contract_address: Optional[str] = None,
):
    if w3 is None:
        w3 = get_web3_client()

    addr = contract_address or os.getenv("CONTRACT_ADDRESS")
    if not addr or addr == "0x0000000000000000000000000000000000000000":
        deployed_json_path = Path("contracts/deployed_contract.json")
        if deployed_json_path.exists():
            with open(deployed_json_path, "r") as f:
                data = json.load(f)
                addr = data.get("address")

    if not addr or addr == "0x0000000000000000000000000000000000000000":
        raise ValueError("Contract address not found. Run scripts/deploy.js first.")

    checksum_address = Web3.to_checksum_address(addr)
    return w3.eth.contract(address=checksum_address, abi=VERIFICATION_REGISTRY_ABI)


def store_record_on_chain(
    record_hash_sha256: str,
    private_key: Optional[str] = None,
    contract_address: Optional[str] = None,
    rpc_url: Optional[str] = None,
    wait_timeout: int = 120,
) -> Dict[str, Any]:
    # submits storeRecord tx to Polygon Amoy
    pk = private_key or os.getenv("PRIVATE_KEY")
    if not pk or pk == "your_testnet_private_key_hex_here":
        raise ValueError(
            "PRIVATE_KEY is missing in .env! A testnet-funded Polygon Amoy wallet is required. "
            "Get free testnet POL at https://faucet.polygon.technology"
        )

    # Clean private key prefix
    if not pk.startswith("0x"):
        pk = "0x" + pk

    w3 = get_web3_client(rpc_url)
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to Polygon Amoy RPC endpoint: {w3.provider.endpoint_uri}")

    account = w3.eth.account.from_key(pk)
    contract = get_contract(w3, contract_address)

    # Format record hash into bytes32
    clean_hash = record_hash_sha256.lower().replace("0x", "")
    if len(clean_hash) != 64:
        raise ValueError(f"Expected 64-character SHA-256 hex string, got {len(clean_hash)} characters.")
    hash_bytes = HexBytes(clean_hash)

    # Fetch wallet nonce & gas parameters
    sender_address = account.address
    nonce = w3.eth.get_transaction_count(sender_address, "pending")
    balance_wei = w3.eth.get_balance(sender_address)
    balance_pol = w3.from_wei(balance_wei, "ether")

    print(f"[Blockchain] Submitter Address: {sender_address} (Balance: {balance_pol:.4f} POL)")
    if balance_wei == 0:
        raise RuntimeError(
            f"Account {sender_address} has 0 POL! "
            "Please fund it with free testnet POL at https://faucet.polygon.technology"
        )

    # Determine gas parameters for Polygon Amoy
    latest_block = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas", w3.to_wei(25, "gwei"))
    priority_fee = w3.to_wei(35, "gwei")
    max_fee = int(base_fee * 2 + priority_fee)

    # Estimate gas with 30% safety margin
    try:
        est_gas = contract.functions.storeRecord(hash_bytes).estimate_gas({"from": sender_address})
        gas_limit = int(est_gas * 1.3)
    except Exception:
        gas_limit = 250000

    # Build transaction
    tx = contract.functions.storeRecord(hash_bytes).build_transaction({
        "from": sender_address,
        "nonce": nonce,
        "gas": gas_limit,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": priority_fee,
        "chainId": 80002,  # Polygon Amoy
    })

    print("[Blockchain] Signing and broadcasting transaction...")
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
    raw_tx = getattr(signed_tx, "raw_transaction", getattr(signed_tx, "rawTransaction", None))
    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    tx_hash_hex = tx_hash.hex()
    print(f"[Blockchain] Transaction broadcast! TxHash: {tx_hash_hex}")
    print(f"[Blockchain] Awaiting confirmation on Polygon Amoy (timeout {wait_timeout}s)...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=wait_timeout)
    print(f"[Blockchain] Tx included in Block #{receipt.blockNumber} (Status: {receipt.status})")

    if receipt.status != 1:
        raise RuntimeError(f"Transaction failed on-chain! Status: {receipt.status}, Tx: {tx_hash_hex}")

    # Extract RecordStored event
    record_id = None
    try:
        events = contract.events.RecordStored().process_receipt(receipt)
        if events:
            record_id = events[0]["args"]["id"]
    except Exception as e:
        print(f"[Blockchain] Event parsing warning: {e}")

    # Fallback to totalRecords view if event log parser didn't resolve
    if record_id is None:
        try:
            record_id = contract.functions.totalRecords().call()
        except Exception:
            record_id = 1

    explorer_tx_url = f"{AMOY_EXPLORER_URL}/tx/{tx_hash_hex}"
    print(f"[Blockchain] Successfully stored record on-chain! Record ID: {record_id}")
    print(f"[Blockchain] Explorer URL: {explorer_tx_url}")

    return {
        "record_id": int(record_id),
        "tx_hash": tx_hash_hex,
        "block_number": receipt.blockNumber,
        "gas_used": receipt.gasUsed,
        "submitter": sender_address,
        "polygonscan_url": explorer_tx_url,
        "record_hash_stored": "0x" + clean_hash,
    }


def verify_record(
    record_id: int,
    local_record_or_file: Union[Dict[str, Any], str],
    contract_address: Optional[str] = None,
    rpc_url: Optional[str] = None,
) -> Dict[str, Any]:
    # compares local record canonical hash with on-chain stored hash
    # Load record dictionary if filepath is passed
    if isinstance(local_record_or_file, (str, Path)):
        record_file = Path(local_record_or_file)
        if not record_file.exists():
            raise FileNotFoundError(f"Local record file not found: {record_file}")
        with open(record_file, "r", encoding="utf-8") as f:
            local_record = json.load(f)
    else:
        local_record = local_record_or_file

    # Recompute canonical local SHA-256 hash
    _, computed_local_hash = compute_canonical_record_hash(local_record)
    local_hash_clean = computed_local_hash.lower().replace("0x", "")

    # Query smart contract view function
    w3 = get_web3_client(rpc_url)
    contract = get_contract(w3, contract_address)

    print(f"[Verification] Reading on-chain record ID #{record_id} from contract {contract.address}...")
    try:
        onchain_record = contract.functions.getRecord(record_id).call()
    except Exception as e:
        # Try public mapping fallback
        onchain_record = contract.functions.records(record_id).call()

    onchain_hash_raw, submitter, timestamp = onchain_record
    onchain_hash_hex = HexBytes(onchain_hash_raw).hex().lower().replace("0x", "")

    is_valid = (local_hash_clean == onchain_hash_hex)

    result = {
        "is_valid": is_valid,
        "record_id": record_id,
        "local_hash": "0x" + local_hash_clean,
        "onchain_hash": "0x" + onchain_hash_hex,
        "submitter": submitter,
        "timestamp": timestamp,
        "message": "Record is authentic and matches on-chain provenance!"
        if is_valid
        else "TAMPER WARNING: Local record hash does NOT match on-chain record!",
    }

    print(f"[Verification] Match Result: {'VERIFIED [OK]' if is_valid else 'MISMATCH [FAILED]'}")
    print(f"   Local Hash:    {result['local_hash']}")
    print(f"   On-Chain Hash: {result['onchain_hash']}")
    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    import sys
    load_dotenv()
    if len(sys.argv) > 2 and sys.argv[1] == "verify":
        # Usage: python src/chain.py verify <id> <path_to_record_json>
        res = verify_record(int(sys.argv[2]), sys.argv[3])
        print(json.dumps(res, indent=2))
    elif len(sys.argv) > 1:
        # Usage: python src/chain.py <sha256_hex>
        res = store_record_on_chain(sys.argv[1])
        print(json.dumps(res, indent=2))
    else:
        print("Usage:")
        print("  Store:  python src/chain.py <record_sha256_hex>")
        print("  Verify: python src/chain.py verify <record_id> <path_to_record.json>")
