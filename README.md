# VeriTrace 🔍⛓️

> **End-to-end Biometric Reverse Search & Immutable Blockchain Provenance Pipeline.**  
> Matches facial media against live social/web records and anchors cryptographic proof of discovery onto the **Polygon Amoy** blockchain.

[![CI](https://github.com/KrishnaDhingra063/VeriTrace-HH-GOA-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/KrishnaDhingra063/VeriTrace-HH-GOA-2026/actions)
[![Network](https://img.shields.io/badge/Blockchain-Polygon%20Amoy%20(80002)-8A2BE2)](https://amoy.polygonscan.com/address/0xe455ac712F23a022f976Dd2b868DD9Ad6aC47066)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ⚡ The Problem & Solution

- **Problem:** AI face-swapping, unauthorized scraping, and deepfakes make it impossible to prove when and where a face first appeared online. Existing reverse-search tools provide ephemeral results that can be deleted or denied.
- **Solution:** VeriTrace captures a face, extracts a 512-dimensional vector embedding, queries public web/social indexes via SerpApi, builds a deterministic canonical record (RFC-8785), and anchors its SHA-256 digest to an immutable smart contract. Anyone can independently re-verify the authenticity of the match against the blockchain.

---

## 📐 Architecture & Pipeline Flow

```text
┌─────────────────┐     ┌──────────────────────┐     ┌────────────────────────┐
│  1. Face Input  │ ──> │ 2. Vector Extraction │ ──> │ 3. Reverse Web Search  │
│  (Upload/Sample)│     │  (RetinaFace/512-d)  │     │ (Social Prioritization)│
└─────────────────┘     └──────────────────────┘     └────────────────────────┘
                                                                  │
┌────────────────────────┐     ┌──────────────────────┐          │
│ 6. Cryptographic Audit │ <── │ 5. Polygon Amoy Sync │ <── 4. Canonical Hash
│ (Live Hash Comparison) │     │ (storeRecord bytes32)│     (RFC-8785 SHA-256)
└────────────────────────┘     └──────────────────────┘
```

---

## ⛓️ Blockchain Details

- **Network:** Polygon Amoy Testnet (`Chain ID: 80002`)
- **Registry Contract:** [`0xe455ac712F23a022f976Dd2b868DD9Ad6aC47066`](https://amoy.polygonscan.com/address/0xe455ac712F23a022f976Dd2b868DD9Ad6aC47066)
- **Explorer:** [View Contract on Polygonscan](https://amoy.polygonscan.com/address/0xe455ac712F23a022f976Dd2b868DD9Ad6aC47066)
- **Unit Economics:**
  - **On-Chain Write (`storeRecord`):** Consumes `~46,000` gas units ($\approx 0.00138\text{ POL}$ / $\$0.0005$).
  - **On-Chain Read (`getRecord`):** Zero gas ($\$0.00$) via free JSON-RPC view calls.

---

## 🚀 Quickstart

### 1. Installation
```bash
# Clone repository
git clone https://github.com/KrishnaDhingra063/VeriTrace-HH-GOA-2026.git
cd VeriTrace-HH-GOA-2026

# Install Node & Python dependencies
npm install
pip install -r requirements.txt
```

### 2. Configure Environment
Create `.env` from template:
```bash
cp .env.example .env
```
Populate `.env`:
```ini
SERPAPI_KEY=your_serpapi_key_here
AMOY_RPC_URL=https://polygon-amoy.drpc.org
PRIVATE_KEY=your_testnet_private_key_here
CONTRACT_ADDRESS=0xe455ac712F23a022f976Dd2b868DD9Ad6aC47066
```

### 3. Run the Application
```bash
# Option A: Interactive Bento UI
python -m streamlit run app.py

# Option B: CLI Pipeline Test
python src/pipeline.py samples/test_face.jpg
```

---

## 🧪 Testing & Verification

```bash
# Run Core Pipeline Unit Tests (Hermetic, offline)
python -m unittest test_pipeline.py

# Run Smart Contract Unit Tests (Hardhat)
npx hardhat test

# Run System Health & Latency Probe
python src/health.py
```

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Biometrics** | DeepFace, RetinaFace, Facenet512 | Face cropping and 512-float vector extraction |
| **Intelligence** | SerpApi (Google Lens / Reverse Search) | Social domain prioritization (`instagram`, `x`, `linkedin`) |
| **Integrity** | RFC-8785 Canonical JSON, SHA-256 | Bit-level deterministic digest computation |
| **Smart Contract** | Solidity `^0.8.20`, Hardhat | Immutable hash registry (`VerificationRegistry.sol`) |
| **Web3 Client** | Web3.py, eth-account | EIP-1559 transaction signing on Polygon Amoy |
| **Interface** | Streamlit, Custom Bento CSS | Responsive dashboard with live tamper audit engine |

---

## ⚠️ Known Limitations

1. **Public Web Index Scope:** Reverse image discovery depends on publicly indexed web pages. Profiles with strict privacy controls or unindexed media cannot be discovered.
2. **Ephemeral Asset Relay:** Reverse search engines require a reachable image URL; images are temporarily uploaded to an ephemeral relay (`freeimage.host` / `catbox.moe`) during search queries.
3. **Hash-Only Privacy:** In strict adherence to data privacy standards, raw biometric embeddings and images are **never stored on-chain**. Only the 32-byte cryptographic digest is recorded.
4. **Testnet Gas:** Transactions require Polygon Amoy testnet tokens (freely available from [Polygon Faucet](https://faucet.polygon.technology/)).

---

## 📄 License
MIT License. Created for Hacker House Goa 2026.
