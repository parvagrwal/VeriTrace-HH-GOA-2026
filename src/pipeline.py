"""
VeriTrace Core Processing Pipeline
Orchestrates face identification, reverse web search, and RFC-8785 canonical hash generation.
"""

import os
import sys
import uuid
import json
import hashlib
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Ensure UTF-8 console output across platforms
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

from src.face import detect_and_embed_face
from src.search import search_reverse_image


def compute_file_sha256(file_path: str) -> str:
    """Computes streaming SHA-256 digest of a local image file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_canonical_record_hash(record_dict: Dict[str, Any]) -> Tuple[str, str]:
    """
    Constructs a deterministic canonical JSON string and computes its SHA-256 digest.
    Applies lexicographical key sorting and compact separators (RFC-8785 standard)
    to guarantee bit-level repeatability across different architectures and languages.
    """
    canonical_data = {
        "record_id": str(record_dict["record_id"]),
        "source_image_sha256": str(record_dict["source_image_sha256"]),
        "matched_url": str(record_dict["matched_url"]),
        "matched_domain": str(record_dict["matched_domain"]),
        "match_type": str(record_dict["match_type"]),
        "match_confidence": float(record_dict["match_confidence"]),
        "result_title": str(record_dict["result_title"]),
        "timestamp_utc": str(record_dict["timestamp_utc"]),
    }

    canonical_json = json.dumps(canonical_data, sort_keys=True, separators=(",", ":"))
    record_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return canonical_json, record_hash


def run_pipeline(
    image_path: str,
    output_records_dir: str = "records",
    use_cropped_face_for_search: bool = True,
    detector_backend: str = "retinaface",
    model_name: str = "Facenet512",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes full VeriTrace pipeline:
    1. Detects face & extracts high-dimensional embedding vector.
    2. Queries live reverse search engine (prioritizing social media matches).
    3. Builds immutable canonical verification ticket & SHA-256 hash.
    4. Persists record JSON to disk for on-chain anchoring.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image does not exist: {image_path}")

    os.makedirs(output_records_dir, exist_ok=True)
    source_sha256 = compute_file_sha256(image_path)
    record_id = str(uuid.uuid4())
    timestamp_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"\n[Pipeline] === Starting VeriTrace Pipeline for {image_path} ===")
    print(f"[Pipeline] Generated Record ID: {record_id}")
    print(f"[Pipeline] Source Image SHA-256: {source_sha256}")

    # Step 1: Detect & Embed Face
    face_data = detect_and_embed_face(
        image_path=image_path,
        detector_backend=detector_backend,
        model_name=model_name,
    )
    cropped_face_path = face_data["face_crop_path"]
    print(f"[Pipeline] Face detected! Crop saved at: {cropped_face_path}")

    # Step 2: Reverse Image Search
    search_target_image = cropped_face_path if use_cropped_face_for_search else image_path
    print(f"[Pipeline] Initiating Reverse Image Search using: {search_target_image}")

    search_result = search_reverse_image(search_target_image, api_key=api_key)
    top_match = search_result["top_match"]

    # Step 3: Build Canonical Verification Record
    record_payload = {
        "record_id": record_id,
        "source_image_sha256": source_sha256,
        "matched_url": top_match["url"],
        "matched_domain": top_match["domain"],
        "match_type": top_match["match_type"],
        "match_confidence": top_match["confidence"],
        "result_title": top_match["title"],
        "timestamp_utc": timestamp_utc,
    }

    canonical_json_str, record_hash = compute_canonical_record_hash(record_payload)
    print(f"[Pipeline] Canonical Record Hash (SHA-256): {record_hash}")

    # Augment record with provenance metadata for disk persistence
    full_saved_record = {
        **record_payload,
        "record_hash_sha256": record_hash,
        "face_metadata": {
            "detector": face_data["detector_backend"],
            "model": face_data["model_name"],
            "embedding_length": face_data["embedding_dimensions"],
            "facial_area": face_data["facial_area"],
            "detection_confidence": face_data["confidence"],
            "crop_path": face_data["face_crop_path"],
        },
        "search_metadata": {
            "public_image_url": search_result["public_image_url"],
            "total_candidates": search_result["total_results"],
            "top_source": top_match["source"],
            "snippet": top_match.get("snippet", ""),
            "is_social": top_match.get("is_social", False),
        },
    }

    # Step 4: Save record to records/<record_id>.json
    record_file_path = os.path.join(output_records_dir, f"{record_id}.json")
    with open(record_file_path, "w", encoding="utf-8") as f:
        json.dump(full_saved_record, f, indent=2)

    print(f"[Pipeline] Verification record persisted to: {record_file_path}")

    return {
        "record_id": record_id,
        "record_hash_sha256": record_hash,
        "canonical_json": canonical_json_str,
        "record_file_path": os.path.abspath(record_file_path),
        "record": full_saved_record,
        "face_data": face_data,
        "search_result": search_result,
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    import sys
    load_dotenv()
    if len(sys.argv) > 1:
        res = run_pipeline(sys.argv[1])
        print(f"\nPipeline finished successfully! Record hash: {res['record_hash_sha256']}")
    else:
        print("Usage: python src/pipeline.py <path_to_image>")
