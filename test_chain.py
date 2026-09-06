import os
import sys

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import time
import hashlib
from dotenv import load_dotenv

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.chain import (
    get_web3_client,
    get_contract,
    store_record_on_chain,
    verify_record,
    AMOY_EXPLORER_URL,
)
from src.pipeline import compute_canonical_record_hash

load_dotenv()


def main():
    print("================================================================")
    print("           VeriTrace Blockchain Verification Test")
    print("================================================================")

    rpc_url = os.getenv("AMOY_RPC_URL", "https://rpc-amoy.polygon.technology")
    private_key = os.getenv("PRIVATE_KEY")
    contract_address = os.getenv("CONTRACT_ADDRESS")

    print(f"[*] RPC Endpoint:     {rpc_url}")
    print(f"[*] Contract Address: {contract_address or '(Not set in .env)'}")

    # 1. Test RPC Connection
    w3 = get_web3_client(rpc_url)
    try:
        is_connected = w3.is_connected()
        print(f"[+] RPC Connection:   {'CONNECTED' if is_connected else 'FAILED'}")
        if not is_connected:
            print("[!] Error: Could not establish connection to Amoy RPC.")
            return
        chain_id = w3.eth.chain_id
        latest_block = w3.eth.block_number
        print(f"[+] Chain ID:         {chain_id} (Expected Amoy: 80002)")
        print(f"[+] Latest Block:     #{latest_block}")
    except Exception as e:
        print(f"[!] RPC Connection Error: {e}")
        return

    # 2. Check Wallet
    if not private_key or "your_testnet_private_key" in private_key:
        print("\n[!] PRIVATE_KEY is not configured in .env.")
        try:
            from eth_account import Account
            temp_acct = Account.create()
            print("    Generated throwaway account for Polygon Amoy:")
            print(f"       Address:    {temp_acct.address}")
            print(f"       PrivateKey: {temp_acct.key.hex()}")
            print("\n    To run real on-chain transactions:")
            print(f"       1. Visit https://faucet.polygon.technology and request Amoy POL for {temp_acct.address}")
            print(f"       2. Put PRIVATE_KEY={temp_acct.key.hex()} in your .env file")
        except Exception:
            pass
        print("\n[+] Read-only checks completed successfully.")
        return

    try:
        clean_pk = private_key if private_key.startswith("0x") else "0x" + private_key
        account = w3.eth.account.from_key(clean_pk)
        balance_wei = w3.eth.get_balance(account.address)
        balance_pol = w3.from_wei(balance_wei, "ether")
        print(f"[+] Wallet Address:   {account.address}")
        print(f"[+] Balance:          {balance_pol:.4f} POL")

        if balance_wei == 0:
            print(f"\n[!] Wallet has 0 POL! Faucet required:")
            print(f"    Visit https://faucet.polygon.technology and request Amoy POL for {account.address}")
            return
    except Exception as e:
        print(f"[!] Invalid PRIVATE_KEY: {e}")
        return

    # 3. Check Contract
    if not contract_address or contract_address.startswith("0x0000"):
        print("\n[!] CONTRACT_ADDRESS not set in .env.")
        print("    Deploy the contract using Hardhat:")
        print("      npm run deploy:amoy")
        print("    Then set the resulting address in .env as CONTRACT_ADDRESS=0x...")
        return

    # 4. Generate Mock Canonical Record
    test_record = {
        "record_id": "test-" + str(int(time.time())),
        "source_image_sha256": hashlib.sha256(b"veritrace-test-image").hexdigest(),
        "matched_url": "https://instagram.com/p/test-photo",
        "matched_domain": "instagram.com",
        "match_type": "social_media_profile",
        "match_confidence": 0.95,
        "result_title": "VeriTrace Test Verification Sample",
        "timestamp_utc": "2026-09-06T12:00:00Z",
    }
    canonical_str, test_hash = compute_canonical_record_hash(test_record)
    print(f"\n[*] Generated Test Record Hash: 0x{test_hash}")

    # 5. Broadcast storeRecord transaction
    print("\n[*] Sending storeRecord transaction to Polygon Amoy...")
    try:
        tx_result = store_record_on_chain(test_hash, private_key=clean_pk)
        record_id = tx_result["record_id"]
        tx_hash = tx_result["tx_hash"]
        print(f"[+] On-Chain Tx Success!")
        print(f"    Record ID:     {record_id}")
        print(f"    Tx Hash:       {tx_hash}")
        print(f"    Explorer Link: {AMOY_EXPLORER_URL}/tx/{tx_hash}")
    except Exception as e:
        print(f"[!] Transaction failed: {e}")
        return

    # 6. Verify Authentic Record
    print(f"\n[*] Reading back record #{record_id} and re-verifying...")
    verification = verify_record(record_id, test_record)
    if verification["is_valid"]:
        print(f"[+] VERIFICATION SUCCESS: Local hash matches on-chain hash exactly!")
        print(f"    Local Hash:    {verification['local_hash']}")
        print(f"    On-Chain Hash: {verification['onchain_hash']}")
        print(f"    Submitter:     {verification['submitter']}")
    else:
        print(f"[!] VERIFICATION FAILED: Hashes do not match.")

    # 7. Test Tamper Detection
    print("\n[*] Testing Tamper Resistance (tampering local record title)...")
    tampered_record = dict(test_record)
    tampered_record["result_title"] = "TAMPERED TITLE - HACK ATTEMPT"
    tampered_result = verify_record(record_id, tampered_record)
    if not tampered_result["is_valid"]:
        print(f"[+] TAMPER DETECTION SUCCESS: Smart contract rejected tampered record!")
        print(f"    Local (Tampered): {tampered_result['local_hash']}")
        print(f"    On-Chain (Truth): {tampered_result['onchain_hash']}")
    else:
        print(f"[!] FAILURE: Tampered record was falsely accepted.")

    print("\n================================================================")
    print("      Blockchain Verification Pipeline Test Completed!")
    print("================================================================")


if __name__ == "__main__":
    main()
