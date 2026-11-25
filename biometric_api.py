import os
import re
import secrets
import time

import cv2
import numpy as np

from flask import Blueprint, jsonify, request, session

from biometric import verify_palm_image
from biometric_storage import (
    load_enrollment,
    save_authentication_log
)

biometric_bp = Blueprint(
    "biometric",
    __name__,
    url_prefix="/api/biometric"
)

THRESHOLD = 0.90


@biometric_bp.get("/health")
def biometric_health():
    return jsonify({
        "ok": True,
        "module": "PALMA Biometric Authentication",
        "enrollment_enabled": False,
        "verification_enabled": bool(
            os.getenv("PALMA_BIOMETRIC_API_TOKEN")
        )
    }), 200


@biometric_bp.post("/verify")
def biometric_verify():

    # Local development access only
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify(error="Access denied"), 403

    # PALMA ADMIN SESSION VERIFICATION
    # Keep the existing server-side API token option.
    token = os.getenv("PALMA_BIOMETRIC_API_TOKEN")
    authorization = request.headers.get("Authorization", "")

    valid_api_token = bool(token) and secrets.compare_digest(
        authorization,
        f"Bearer {token}"
    )

    if not valid_api_token:
        if session.get("biometric_admin") is not True:
            if not token:
                return jsonify(error="Verification is disabled"), 503
            return jsonify(error="Unauthorized"), 401

        origin = request.headers.get("Origin", "")
        expected_origin = request.host_url.rstrip("/")

        if origin != expected_origin:
            return jsonify(error="Invalid request origin"), 403

        expected_csrf = session.get("admin_csrf_token")
        supplied_csrf = request.headers.get("X-CSRF-Token", "")

        if (
            not isinstance(expected_csrf, str)
            or not secrets.compare_digest(
                supplied_csrf,
                expected_csrf
            )
        ):
            return jsonify(error="Invalid security token"), 403

    start = time.perf_counter()

    user_id = request.form.get("user_id", "").strip()
    uploaded_file = request.files.get("image")

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", user_id):
        return jsonify(error="Invalid user ID"), 400

    if uploaded_file is None:
        return jsonify(error="Palm image is required"), 400

    image_bytes = uploaded_file.read(8 * 1024 * 1024 + 1)

    if not image_bytes or len(image_bytes) > 8 * 1024 * 1024:
        return jsonify(error="Invalid image size"), 400

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        return jsonify(error="Invalid image"), 422

    try:
        enrollment = load_enrollment(user_id)
    except (RuntimeError, ValueError):
        return jsonify(error="Biometric service unavailable"), 503

    if enrollment is None:
        return jsonify({
            "status": "Failed Authentication"
        }), 200

    result = verify_palm_image(
        enrollment,
        image,
        enrollment["hand_side"]
    )

    if result.get("status") != "score_calculated":
        return jsonify({
            "status": "Invalid Image",
            "message": "Palm verification could not be completed"
        }), 422

    score = float(result["average_score"])
    accepted = score >= THRESHOLD

    outcome = (
        "Successful Authentication"
        if accepted
        else "Failed Authentication"
    )

    duration_ms = round(
        (time.perf_counter() - start) * 1000, 2
    )

    save_authentication_log(
        user_id,
        "Successful" if accepted else "Failed",
        score,
        duration_ms
    )

    return jsonify({
        "user_id": user_id,
        "status": outcome,
        "score": round(score, 4),
        "threshold": THRESHOLD,
        "threshold_type": "experimental",
        "duration_ms": duration_ms
    }), 200
