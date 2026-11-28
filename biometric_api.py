import os
import re
import secrets
import time

import cv2
import numpy as np

from flask import Blueprint, current_app, jsonify, request, session

from biometric import verify_palm_image
from biometric_storage import (
    load_enrollment,
    save_authentication_log,
    list_authentication_logs
)

biometric_bp = Blueprint(
    "biometric",
    __name__,
    url_prefix="/api/biometric"
)

THRESHOLD = 0.90


@biometric_bp.after_request
def prevent_biometric_caching(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@biometric_bp.get("/history")
def biometric_history():
    """Read-only recent audit history for a signed-in local administrator."""
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify(error="Local access only"), 403

    if session.get("biometric_admin") is not True:
        return jsonify(error="Admin login required"), 401

    user_id = request.args.get("user_id", "").strip() or None
    try:
        rows = list_authentication_logs(user_id=user_id, limit=50)
    except ValueError:
        return jsonify(error="Invalid participant ID"), 400
    except Exception:
        current_app.logger.exception("Unable to load authentication history")
        return jsonify(error="Authentication history unavailable"), 503

    return jsonify(ok=True, records=rows, count=len(rows)), 200


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
        save_authentication_log(user_id, "Invalid Image", None,
                                round((time.perf_counter() - start) * 1000, 2))
        return jsonify(status="Invalid Image", message="Image could not be decoded"), 422

    if image.shape[0] * image.shape[1] > 16_000_000:
        save_authentication_log(user_id, "Invalid Image", None,
                                round((time.perf_counter() - start) * 1000, 2))
        return jsonify(status="Invalid Image", message="Image is too large"), 422

    try:
        enrollment = load_enrollment(user_id)
    except (RuntimeError, ValueError):
        return jsonify(error="Biometric service unavailable"), 503

    if enrollment is None:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        save_authentication_log(user_id, "Failed", None, duration_ms)
        return jsonify(status="Authentication Failed", score=None,
                       threshold=THRESHOLD, duration_ms=duration_ms), 200

    result = verify_palm_image(
        enrollment,
        image,
        enrollment["hand_side"]
    )

    if result.get("status") != "score_calculated":
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        save_authentication_log(user_id, "Invalid Image", None, duration_ms)
        return jsonify({
            "status": "Invalid Image",
            "message": "; ".join(str(reason) for reason in (result.get("reasons") or [])) or "Palm verification could not be completed",
            "duration_ms": duration_ms,
        }), 422

    score = float(result["average_score"])
    accepted = score >= THRESHOLD

    outcome = (
        "Authentication Successful"
        if accepted
        else "Authentication Failed"
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

    response = {
        "user_id": user_id,
        "status": outcome,
        "score": round(score, 4),
        "threshold": THRESHOLD,
        "threshold_type": "experimental",
        "duration_ms": duration_ms,
    }

    # In-memory visual feedback, only if the authenticated requester opts in.
    # Failure to render preview images must not change the biometric decision.
    if request.form.get("include_stages") == "yes":
        try:
            from biometric_visuals import render_processing_stages
            response["stages"] = render_processing_stages(image)
        except Exception:
            current_app.logger.warning("Palm processing preview unavailable")
            response["stage_message"] = "Processing previews unavailable for this image."

    return jsonify(response), 200
