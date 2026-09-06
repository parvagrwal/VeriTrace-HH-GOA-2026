# VeriTrace

Reverse face search and on-chain verification pipeline for Polygon Amoy testnet.

Given an input photo, VeriTrace:
1. Detects and extracts the face embedding using `deepface` (RetinaFace / Facenet512).
2. Runs a reverse search using SerpApi (prioritizing social media platforms like Instagram, X, LinkedIn, and Reddit).
3. Generates a canonical JSON record containing source image hash, matched URL, timestamp, and confidence score.
4. Stores the SHA-256 hash on-chain via a Solidity contract (`VerificationRegistry.sol`) on Polygon Amoy.
5. Provides an audit interface to re-verify local records against the immutable on-chain record.

---

## Architecture

```text
[Input Image] 
      │
      ├──> Face Detection & Embedding (deepface, RetinaFace/Facenet512)
      │
      ├──> Ephemeral Upload -> Reverse Search (SerpApi)
      │      └──> Social Domain Prioritization & Scoring
      │
      ├──> Canonical JSON Construction -> SHA-256 Digest
      │
      ├──> Smart Contract Call: storeRecord(bytes32 recordHash)
      │      └──> Polygon Amoy Testnet (Chain ID 80002)
      │
      └──> Re-verification View: local hash vs on-chain hash
```

---

## Tech Stack

- **Python 3.11 / 3.13**
- **DeepFace**: Face detection and 512-d feature embedding.
- **SerpApi**: Reverse image search engine.
- **Solidity ^0.8.20 + Hardhat**: On-chain verification registry.
- **Web3.py**: Contract interactions and transaction signing.
- **Streamlit**: Web demo interface.

---

## Setup & Running

### 1. Dependencies

Install node packages (Hardhat):
```bash
npm install
```

Install Python packages:
```bash
pip install -r requirements.txt
```

### 2. Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Set the values in `.env`:
- `SERPAPI_KEY`: API key from serpapi.com.
- `AMOY_RPC_URL`: `https://polygon-amoy.drpc.org` (or another Amoy RPC).
- `PRIVATE_KEY`: Private key of your testnet wallet.
- `CONTRACT_ADDRESS`: Deployed registry contract address.

### 3. Deploy Contract to Polygon Amoy

Compile contracts:
```bash
npx hardhat compile
```

Deploy to Amoy testnet:
```bash
node scripts/deploy.js --network amoy
```

Copy the printed contract address into your `.env` as `CONTRACT_ADDRESS`.

### 4. CLI Verification Test

Run the standalone chain test script to check RPC connectivity, wallet balance, and testnet round-trip:
```bash
python test_chain.py
```

### 5. Launch the Web Interface

Start the Streamlit app:
```bash
python -m streamlit run app.py
```

---

## Project Structure

```text
├── contracts/
│   ├── VerificationRegistry.sol    # Smart contract
│   └── deployed_contract.json      # Address and ABI artifact
├── scripts/
│   └── deploy.js                   # Deployment script
├── test/
│   └── VerificationRegistry.test.js# Hardhat contract tests
├── src/
│   ├── face.py                     # Face detection and embedding
│   ├── search.py                   # Reverse search and ranking
│   ├── pipeline.py                 # Pipeline and canonical hashing
│   └── chain.py                    # Web3.py Polygon Amoy integration
├── app.py                          # Streamlit interface
├── test_chain.py                   # CLI verification script
├── requirements.txt
├── package.json
└── README.md
```

---

## Blockchain Details

- **Network**: Polygon Amoy Testnet (`chainId: 80002`)
- **Contract Address**: `0xe455ac712F23a022f976Dd2b868DD9Ad6aC47066`
- **Explorer**: [https://amoy.polygonscan.com/address/0xe455ac712F23a022f976Dd2b868DD9Ad6aC47066](https://amoy.polygonscan.com/address/0xe455ac712F23a022f976Dd2b868DD9Ad6aC47066)

Polygon Amoy was chosen for fast block confirmation (~2 seconds), minimal gas costs, and EVM compatibility while testing without real financial exposure.

---

## Limitations

- **Indexed Images Only**: Reverse image search queries public web indexes; private or unindexed social profiles cannot be matched.
- **Ephemeral Hosting**: Reverse search requires a public image URL, so images are uploaded to temporary hosting during search queries.
- **Hash vs Content**: Only the SHA-256 hash is recorded on-chain, keeping gas costs low and preserving privacy. To verify, the verifier must have access to the local JSON record.
- **Testnet**: Runs on Polygon Amoy testnet, suitable for testing and demo purposes.
