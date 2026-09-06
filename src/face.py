import os
import sys

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image

try:
    from deepface import DeepFace
except ImportError:
    DeepFace = None


def detect_and_embed_face(
    image_path: str,
    output_crop_dir: str = "records/crops",
    detector_backend: str = "retinaface",
    model_name: str = "Facenet512",
    fallback_detectors: Optional[list] = None,
) -> Dict[str, Any]:
    # crops face from image and computes embedding vector
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")

    if DeepFace is None:
        raise ImportError("DeepFace is not installed. Please install it using requirements.txt.")

    os.makedirs(output_crop_dir, exist_ok=True)
    detectors = [detector_backend]
    if fallback_detectors:
        detectors.extend([d for d in fallback_detectors if d not in detectors])
    else:
        detectors.extend([d for d in ["mtcnn", "opencv"] if d != detector_backend])

    extracted_faces = None
    used_detector = detector_backend

    # Try detectors sequentially with graceful fallback
    for detector in detectors:
        try:
            print(f"[Face] Attempting face extraction with detector: {detector}...")
            faces = DeepFace.extract_faces(
                img_path=image_path,
                detector_backend=detector,
                align=True,
                enforce_detection=True,
            )
            if faces and len(faces) > 0:
                extracted_faces = faces
                used_detector = detector
                break
        except Exception as e:
            print(f"[Face] Detector '{detector}' failed or found no face: {e}")

    # Fallback to lenient mode if strict detection failed
    if not extracted_faces:
        print("[Face] Retrying with enforce_detection=False (best effort crop)...")
        try:
            faces = DeepFace.extract_faces(
                img_path=image_path,
                detector_backend="opencv",
                align=True,
                enforce_detection=False,
            )
            if faces:
                extracted_faces = faces
                used_detector = "opencv-lenient"
        except Exception as e:
            raise RuntimeError(f"Could not extract face from image: {e}")

    if not extracted_faces:
        raise ValueError(f"No face detected in {image_path}")

    # Pick the most prominent face (largest area or highest confidence)
    best_face = max(
        extracted_faces,
        key=lambda f: (f.get("facial_area", {}).get("w", 0) * f.get("facial_area", {}).get("h", 0)),
    )

    face_array = best_face["face"]  # Normalized float array [0, 1] in RGB
    facial_area = best_face.get("facial_area", {})
    confidence = float(best_face.get("confidence", 0.95))

    # Convert normalized RGB array [0, 1] to uint8 [0, 255] RGB and save
    if face_array.max() <= 1.0:
        face_uint8 = (face_array * 255).astype(np.uint8)
    else:
        face_uint8 = face_array.astype(np.uint8)

    base_name = Path(image_path).stem
    crop_filename = f"{base_name}_face_{used_detector}.jpg"
    crop_path = os.path.join(output_crop_dir, crop_filename)

    # Convert to PIL and save
    crop_img = Image.fromarray(face_uint8)
    crop_img.save(crop_path, format="JPEG", quality=95)
    print(f"[Face] Saved aligned face crop to {crop_path}")

    # Compute facial embedding representation
    print(f"[Face] Computing embedding vector using model '{model_name}'...")
    embedding = []
    models_to_try = [model_name]
    if "ArcFace" not in models_to_try:
        models_to_try.append("ArcFace")
    if "Facenet512" not in models_to_try:
        models_to_try.append("Facenet512")

    used_model = model_name
    for m in models_to_try:
        try:
            representations = DeepFace.represent(
                img_path=crop_path,
                model_name=m,
                detector_backend="skip",  # Already cropped & aligned
                enforce_detection=False,
            )
            if representations and isinstance(representations, list):
                embedding = representations[0]["embedding"]
                used_model = m
                break
        except Exception as e:
            print(f"[Face] Model '{m}' failed: {e}. Trying fallback...")

    if not embedding:
        print("[Face] Computing fallback representation from source image...")
        for m in models_to_try:
            try:
                representations = DeepFace.represent(
                    img_path=image_path,
                    model_name=m,
                    detector_backend=used_detector.replace("-lenient", ""),
                    enforce_detection=False,
                )
                if representations and isinstance(representations, list):
                    embedding = representations[0]["embedding"]
                    used_model = m
                    break
            except Exception:
                continue

    return {
        "face_crop_path": os.path.abspath(crop_path),
        "embedding": embedding,
        "embedding_dimensions": len(embedding),
        "facial_area": facial_area,
        "confidence": confidence,
        "detector_backend": used_detector,
        "model_name": used_model,
        "source_image_path": os.path.abspath(image_path),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = detect_and_embed_face(sys.argv[1])
        print(f"Face extracted! Embedding dimension: {len(result['embedding'])}")
        print(f"Crop saved at: {result['face_crop_path']}")
    else:
        print("Usage: python src/face.py <path_to_image>")
