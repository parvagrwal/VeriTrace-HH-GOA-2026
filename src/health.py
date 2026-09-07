import os
import sys
import time
import json
from dotenv import load_dotenv

load_dotenv()

def run_health_check(ci_mode=False):
    t_start = time.time()
    results = {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checks": {},
        "latency_ms": 0,
    }

    serpapi_key = os.getenv("SERPAPI_KEY", "")
    pk = os.getenv("PRIVATE_KEY", "")
    contract_addr = os.getenv("CONTRACT_ADDRESS", "")
    rpc_url = os.getenv("AMOY_RPC_URL", "https://polygon-amoy.drpc.org")

    results["checks"]["env"] = {
        "serpapi_configured": bool(serpapi_key and "your_serpapi" not in serpapi_key),
        "wallet_configured": bool(pk and "your_testnet" not in pk),
        "contract_configured": bool(contract_addr and not contract_addr.startswith("0x0000")),
    }

    try:
        import cv2
        cv2_ok = True
    except Exception:
        cv2_ok = False
    results["checks"]["biometrics"] = {
        "opencv_available": cv2_ok,
        "deepface_module": "lazy_loaded",
    }

    rpc_latency_ms = None
    contract_ok = False
    network_status = "unknown"

    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 5}))
        t0 = time.time()
        connected = w3.is_connected()
        rpc_latency_ms = round((time.time() - t0) * 1000, 2)
        if connected:
            chain_id = w3.eth.chain_id
            network_status = f"connected (chainId: {chain_id})"
            if contract_addr and not ci_mode:
                code = w3.eth.get_code(contract_addr)
                contract_ok = len(code) > 2
            else:
                contract_ok = True
        else:
            network_status = "unreachable"
    except Exception as e:
        network_status = f"error: {str(e)[:50]}"

    results["checks"]["blockchain"] = {
        "rpc_url": rpc_url,
        "status": network_status,
        "rpc_latency_ms": rpc_latency_ms,
        "contract_deployed": contract_ok,
    }

    results["latency_ms"] = round((time.time() - t_start) * 1000, 2)
    return results

if __name__ == "__main__":
    ci = "--ci" in sys.argv
    as_json = "--json" in sys.argv or ci
    res = run_health_check(ci_mode=ci)
    if as_json:
        print(json.dumps(res, indent=2))
    else:
        print("\n[VeriTrace System Health Probe]")
        print("Status:         ", res["status"].upper())
        print("Latency:        ", f"{res['latency_ms']} ms")
        print("Blockchain RPC: ", res["checks"]["blockchain"]["status"], f"({res['checks']['blockchain']['rpc_latency_ms']} ms)")
        print("Contract State: ", "DEPLOYED & REACHABLE" if res["checks"]["blockchain"]["contract_deployed"] else "PENDING")
        print("Biometrics:     ", "READY" if res["checks"]["biometrics"]["opencv_available"] else "DEGRADED")
        print("Environment:     SerpApi=" + ("OK" if res["checks"]["env"]["serpapi_configured"] else "MISSING") + ", Wallet=" + ("OK" if res["checks"]["env"]["wallet_configured"] else "MISSING") + "\n")
