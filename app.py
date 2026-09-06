import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import tempfile
from pathlib import Path
from PIL import Image
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.face import detect_and_embed_face
from src.search import search_reverse_image
from src.pipeline import run_pipeline, compute_canonical_record_hash
from src.chain import (
    store_record_on_chain,
    verify_record,
    get_web3_client,
    get_contract,
    AMOY_EXPLORER_URL,
)

load_dotenv()

st.set_page_config(
    page_title="VeriTrace",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .app-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .app-subtitle {
        color: #64748b;
        font-size: 0.95rem;
        margin-bottom: 1.2rem;
    }
    .tag-social {
        background-color: #059669;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 500;
        font-size: 0.8rem;
        display: inline-block;
    }
    .tag-web {
        background-color: #475569;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 500;
        font-size: 0.8rem;
        display: inline-block;
    }
    .hash-code {
        background-color: #1e293b;
        color: #38bdf8;
        font-family: monospace;
        padding: 8px 12px;
        border-radius: 6px;
        word-break: break-all;
        font-size: 0.85rem;
    }
    .alert-ok {
        background-color: #064e3b;
        color: #d1fae5;
        border: 1px solid #10b981;
        padding: 12px;
        border-radius: 6px;
        font-weight: 500;
    }
    .alert-tamper {
        background-color: #7f1d1d;
        color: #fee2e2;
        border: 1px solid #ef4444;
        padding: 12px;
        border-radius: 6px;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="app-title">VeriTrace</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">Reverse Image Search & On-Chain Provenance Registry</div>', unsafe_allow_html=True)

# Settings in sidebar
st.sidebar.subheader("Configuration")

env_serpapi = os.getenv("SERPAPI_KEY", "")
env_amoy_rpc = os.getenv("AMOY_RPC_URL", "https://polygon-amoy.drpc.org")
env_pk = os.getenv("PRIVATE_KEY", "")
env_contract = os.getenv("CONTRACT_ADDRESS", "")

serpapi_status = "configured" if (env_serpapi and "your_serpapi" not in env_serpapi) else "missing"
chain_status = "configured" if (env_pk and "your_testnet" not in env_pk) else "missing"
contract_status = "configured" if (env_contract and not env_contract.startswith("0x0000")) else "missing"

st.sidebar.text(f"SerpApi: {serpapi_status}")
st.sidebar.text(f"Wallet key: {chain_status}")
st.sidebar.text(f"Contract: {contract_status}")

with st.sidebar.expander("Settings / Overrides", expanded=False):
    override_serpapi = st.text_input("SerpApi Key", value=env_serpapi, type="password")
    override_contract = st.text_input("Contract Address", value=env_contract)
    override_pk = st.text_input("Private Key", value=env_pk, type="password")
    override_rpc = st.text_input("RPC Endpoint", value=env_amoy_rpc)

active_serpapi = override_serpapi or env_serpapi
active_contract = override_contract or env_contract
active_pk = override_pk or env_pk
active_rpc = override_rpc or env_amoy_rpc

st.sidebar.subheader("Model options")
detector_backend = st.sidebar.selectbox("Detector", ["retinaface", "mtcnn", "opencv"], index=0)
embedding_model = st.sidebar.selectbox("Embedding Model", ["Facenet512", "ArcFace", "Facenet"], index=0)
search_target = st.sidebar.radio("Search input", ["Cropped Face", "Original Image"], index=0)
use_crop = (search_target == "Cropped Face")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("1. Input Image")
    sample_dir = Path("samples")
    sample_files = [f.name for f in sample_dir.glob("*.*") if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]
    
    input_mode = st.radio("Source", ["Upload file", "Sample library" if sample_files else "Upload file"])
    selected_image_path = None

    if input_mode == "Sample library" and sample_files:
        chosen_sample = st.selectbox("Choose sample", sample_files)
        selected_image_path = str(sample_dir / chosen_sample)
        st.image(selected_image_path, caption=chosen_sample, use_container_width=True)
    else:
        uploaded_file = st.file_uploader("Choose an image (JPG, PNG)", type=["jpg", "jpeg", "png", "webp"])
        if uploaded_file is not None:
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            selected_image_path = temp_path
            st.image(selected_image_path, caption="Uploaded image", use_container_width=True)

    run_btn = st.button("Run Pipeline", type="primary", disabled=(selected_image_path is None))

if run_btn and selected_image_path:
    with st.spinner("Processing face detection and search..."):
        try:
            with st.status("Detecting face & extracting embedding...", expanded=True) as s1:
                face_data = detect_and_embed_face(
                    image_path=selected_image_path,
                    detector_backend=detector_backend,
                    model_name=embedding_model,
                )
                s1.update(label="Face detected", state="complete")

            with st.status("Querying reverse image search...", expanded=True) as s2:
                search_image = face_data["face_crop_path"] if use_crop else selected_image_path
                search_data = search_reverse_image(
                    search_image,
                    api_key=active_serpapi,
                )
                s2.update(label="Search completed", state="complete")

            with st.status("Creating canonical record...", expanded=True) as s3:
                import hashlib
                with open(selected_image_path, "rb") as f:
                    src_hash = hashlib.sha256(f.read()).hexdigest()

                import uuid, datetime
                rec_id = str(uuid.uuid4())
                timestamp_now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                top_match = search_data["top_match"]
                canonical_payload = {
                    "record_id": rec_id,
                    "source_image_sha256": src_hash,
                    "matched_url": top_match["url"],
                    "matched_domain": top_match["domain"],
                    "match_type": top_match["match_type"],
                    "match_confidence": top_match["confidence"],
                    "result_title": top_match["title"],
                    "timestamp_utc": timestamp_now,
                }
                canonical_json_str, record_hash = compute_canonical_record_hash(canonical_payload)

                full_saved = {
                    **canonical_payload,
                    "record_hash_sha256": record_hash,
                    "face_metadata": {
                        "detector": face_data["detector_backend"],
                        "model": face_data["model_name"],
                        "facial_area": face_data["facial_area"],
                        "embedding_dimensions": face_data["embedding_dimensions"],
                    },
                    "search_metadata": {
                        "public_image_url": search_data["public_image_url"],
                        "top_source": top_match["source"],
                    },
                }

                rec_file = os.path.join("records", f"{rec_id}.json")
                with open(rec_file, "w", encoding="utf-8") as f:
                    json.dump(full_saved, f, indent=2)

                s3.update(label="Record saved", state="complete")

            tx_data = None
            if active_pk and "your_testnet" not in active_pk and active_contract and not active_contract.startswith("0x0000"):
                with st.status("Writing record hash to Polygon Amoy...", expanded=True) as s4:
                    try:
                        tx_data = store_record_on_chain(
                            record_hash_sha256=record_hash,
                            private_key=active_pk,
                            contract_address=active_contract,
                            rpc_url=active_rpc,
                        )
                        s4.update(label="Transaction confirmed on-chain", state="complete")
                    except Exception as e:
                        s4.update(label=f"Blockchain write error: {e}", state="error")
                        st.error(f"Blockchain error: {e}")

            st.session_state["pipeline_result"] = {
                "face_data": face_data,
                "search_data": search_data,
                "canonical_payload": canonical_payload,
                "record_hash": record_hash,
                "full_saved": full_saved,
                "record_file": rec_file,
                "tx_data": tx_data,
            }

        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.exception(e)

if "pipeline_result" in st.session_state:
    res = st.session_state["pipeline_result"]
    face = res["face_data"]
    search = res["search_data"]
    top = search["top_match"]
    tx = res.get("tx_data")

    with col_right:
        st.subheader("2. Face Analysis")
        c1, c2 = st.columns([1, 1])
        with c1:
            st.image(face["face_crop_path"], caption=f"Crop ({face['detector_backend']})", width=180)
        with c2:
            st.metric("Confidence", f"{face['confidence'] * 100:.1f}%")
            st.metric("Embedding size", f"{face['embedding_dimensions']} floats")
            st.caption(f"Model: {face['model_name']}")

        st.divider()

        st.subheader("3. Reverse Search Results")
        tag_class = "tag-social" if top["is_social"] else "tag-web"
        tag_label = "Social profile" if top["is_social"] else "Web page"

        st.markdown(f'<span class="{tag_class}">{tag_label}</span>', unsafe_allow_html=True)
        st.markdown(f"**Domain:** `{top['domain']}` | **Source:** {top['source']}")
        st.markdown(f"**Snippet:** {top['title']}")
        if top["url"] and top["url"].startswith("http"):
            st.markdown(f"[{top['url']}]({top['url']})")
        st.progress(top["confidence"], text=f"Match confidence: {int(top['confidence'] * 100)}%")

        if top.get("thumbnail"):
            st.image(top["thumbnail"], caption="Match thumbnail", width=120)

        with st.expander(f"All matches ({search['total_results']})"):
            for cand in search.get("candidates", []):
                st.markdown(f"- **#{cand['rank']}** [{cand['domain']}]({cand['url']}) - {cand['title']} ({cand['confidence']})")

    st.divider()

    col_rec, col_chain = st.columns([1, 1], gap="large")

    with col_rec:
        st.subheader("4. Canonical Record")
        st.markdown(f"**Record ID:** `{res['canonical_payload']['record_id']}`")
        st.markdown(f"**SHA-256 Digest:**")
        st.markdown(f'<div class="hash-code">0x{res["record_hash"]}</div>', unsafe_allow_html=True)
        st.json(res["canonical_payload"])

        st.download_button(
            label="Download JSON Record",
            data=json.dumps(res["full_saved"], indent=2),
            file_name=f"record_{res['canonical_payload']['record_id']}.json",
            mime="application/json",
        )

    with col_chain:
        st.subheader("5. Polygon Amoy Status")
        if tx:
            st.success("Record anchored on Polygon Amoy")
            st.markdown(f"**On-chain ID:** `#{tx['record_id']}`")
            st.markdown(f"**Block:** `#{tx['block_number']}` | **Gas used:** `{tx['gas_used']}`")
            st.markdown(f"**Submitter:** `{tx['submitter']}`")
            st.markdown(f"**Explorer:** [{tx['polygonscan_url']}]({tx['polygonscan_url']})")
        else:
            st.warning("Not yet recorded on-chain.")
            if st.button("Publish to Polygon Amoy"):
                with st.spinner("Submitting tx..."):
                    try:
                        tx_new = store_record_on_chain(
                            record_hash_sha256=res["record_hash"],
                            private_key=active_pk,
                            contract_address=active_contract,
                            rpc_url=active_rpc,
                        )
                        res["tx_data"] = tx_new
                        st.session_state["pipeline_result"] = res
                        st.rerun()
                    except Exception as e:
                        st.error(f"Submission failed: {e}")

    st.divider()
    st.subheader("6. On-Chain Verification")
    st.caption("Reads on-chain hash by ID and compares it against local record digest.")

    col_v1, col_v2 = st.columns([1, 1])
    with col_v1:
        simulate_tamper = st.checkbox(
            "Simulate tampered local record (alters title to test mismatch)",
            value=False,
        )

    with col_v2:
        reverify_btn = st.button("Verify Record Integrity", type="secondary")

    if reverify_btn:
        if not tx and not active_contract:
            st.error("Missing contract or record ID.")
        else:
            record_id_to_check = tx["record_id"] if tx else 1
            payload_to_test = dict(res["canonical_payload"])

            if simulate_tamper:
                payload_to_test["result_title"] = "MODIFIED UNVERIFIED CONTENT"
                payload_to_test["match_confidence"] = 0.999

            with st.spinner("Calling contract..."):
                try:
                    verify_res = verify_record(
                        record_id=record_id_to_check,
                        local_record_or_file=payload_to_test,
                        contract_address=active_contract,
                        rpc_url=active_rpc,
                    )

                    if verify_res["is_valid"]:
                        st.markdown(
                            f"""
                            <div class="alert-ok">
                                <strong>VERIFIED</strong> - Local record hash matches on-chain hash.
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"""
                            <div class="alert-tamper">
                                <strong>MISMATCH DETECTED</strong> - Local hash does not match on-chain record!
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    c_h1, c_h2 = st.columns(2)
                    with c_h1:
                        st.markdown("**Local Hash:**")
                        st.markdown(f'<div class="hash-code">{verify_res["local_hash"]}</div>', unsafe_allow_html=True)
                    with c_h2:
                        st.markdown("**On-Chain Hash:**")
                        st.markdown(f'<div class="hash-code">{verify_res["onchain_hash"]}</div>', unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Verification call failed: {e}")
