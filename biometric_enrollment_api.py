
import io
import re
import secrets
import sqlite3
import tempfile
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from flask import Blueprint, current_app, jsonify, request, session

from biometric import prepare_enrollment
from biometric_storage import load_enrollment, save_enrollment, delete_enrollment

enrollment_bp = Blueprint(
    "palma_enrollment",
    __name__,
    url_prefix="/api/biometric"
)

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000


@enrollment_bp.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@enrollment_bp.post("/enroll")
def enroll_palm():

    # Authorized local administration only
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify(error="Local access only"), 403

    if session.get("biometric_admin") is not True:
        return jsonify(error="Admin login required"), 401

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

    user_id = request.form.get("user_id", "").strip()
    hand_side = request.form.get("hand_side", "").strip().lower()
    consent = request.form.get("consent", "") == "true"
    images = request.files.getlist("images")

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", user_id):
        return jsonify(error="Invalid participant ID"), 400

    if hand_side not in ("left", "right"):
        return jsonify(error="Select left or right hand"), 400

    if not consent:
        return jsonify(error="Participant consent is required"), 400

    if len(images) != 3:
        return jsonify(error="Exactly 3 palm images are required"), 400

    # Never replace an existing biometric identity
    try:
        existing = load_enrollment(user_id)
    except Exception:
        current_app.logger.exception(
            "Unable to check biometric enrollment"
        )
        return jsonify(error="Biometric storage unavailable"), 503

    if existing is not None:
        return jsonify(
            error="Participant ID is already enrolled"
        ), 409

    try:
        with tempfile.TemporaryDirectory(
            prefix="palma_enroll_"
        ) as temporary_directory:

            image_paths = []

            for number, uploaded in enumerate(images, start=1):

                content = uploaded.read(MAX_IMAGE_BYTES + 1)

                if not content or len(content) > MAX_IMAGE_BYTES:
                    return jsonify(
                        error=f"Image {number} must be under 5 MB"
                    ), 413

                try:
                    with Image.open(io.BytesIO(content)) as photo:
                        image_format = photo.format
                        width, height = photo.size

                except (
                    UnidentifiedImageError,
                    OSError,
                    ValueError
                ):
                    return jsonify(
                        error=f"Image {number} is not a valid image"
                    ), 422

                if image_format not in ("JPEG", "PNG", "MPO"):
                    return jsonify(
                        error=f"Image {number} must be JPG or PNG"
                    ), 422

                if (
                    width < 256
                    or height < 256
                    or width * height > MAX_IMAGE_PIXELS
                ):
                    return jsonify(
                        error=f"Image {number} has invalid dimensions"
                    ), 422

                extension = (
                    ".jpg" if image_format in ("JPEG", "MPO") else ".png"
                )

                image_path = (
                    Path(temporary_directory)
                    / f"palm_{number}{extension}"
                )


                # PALMA MPO IMAGE SUPPORT
                if image_format == "MPO":
                    try:
                        with Image.open(io.BytesIO(content)) as photo:
                            photo.seek(0)
                            primary = ImageOps.exif_transpose(photo)
                            primary = primary.convert("RGB")

                            output = io.BytesIO()
                            primary.save(
                                output,
                                format="JPEG",
                                quality=95,
                                subsampling=0
                            )
                            content = output.getvalue()

                    except (OSError, ValueError):
                        return jsonify(
                            error=f"Image {number} MPO conversion failed"
                        ), 422

                image_path.write_bytes(content)
                image_paths.append(str(image_path))

            # Extract biometric features from 3 palm images
            enrollment = prepare_enrollment(
                user_id=user_id,
                hand_side=hand_side,
                image_paths=image_paths,
                consent=True
            )

            # Store encrypted templates, not uploaded photos
            result = save_enrollment(enrollment)

    except ValueError as error:
        return jsonify(
            error="Palm image quality or validation failed",
            detail=str(error)
        ), 422

    except sqlite3.IntegrityError:
        return jsonify(
            error="Participant ID is already enrolled"
        ), 409

    except RuntimeError:
        current_app.logger.exception(
            "Biometric encryption or storage unavailable"
        )
        return jsonify(
            error="Biometric storage unavailable"
        ), 503

    except Exception:
        current_app.logger.exception(
            "Unexpected palm enrollment failure"
        )
        return jsonify(
            error="Palm enrollment could not be completed"
        ), 500

    return jsonify(
        status=result["status"],
        user_id=result["user_id"],
        hand_side=result["hand_side"],
        template_count=result["template_count"]
    ), 201


@enrollment_bp.post("/delete-enrollment")
def delete_palm_enrollment():
    """Delete participant enrollment and history with admin authorization."""

    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify(error="Local access only"), 403

    if session.get("biometric_admin") is not True:
        return jsonify(error="Admin login required"), 401

    origin = request.headers.get("Origin", "")
    expected_origin = request.host_url.rstrip("/")

    if origin != expected_origin:
        return jsonify(error="Invalid request origin"), 403

    expected_csrf = session.get("admin_csrf_token")
    supplied_csrf = request.headers.get("X-CSRF-Token", "")

    if (
        not isinstance(expected_csrf, str)
        or not secrets.compare_digest(supplied_csrf, expected_csrf)
    ):
        return jsonify(error="Invalid security token"), 403

    if not request.is_json:
        return jsonify(error="JSON request required"), 415

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="Invalid JSON data"), 400

    user_id = data.get("user_id", "")
    confirmation = data.get("confirm_user_id", "")

    if not isinstance(user_id, str):
        return jsonify(error="Invalid participant ID"), 400

    user_id = user_id.strip()

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", user_id):
        return jsonify(error="Invalid participant ID"), 400

    if confirmation != user_id:
        return jsonify(error="Participant ID confirmation required"), 400

    try:
        result = delete_enrollment(user_id)
    except Exception:
        current_app.logger.exception("Biometric deletion failed")
        return jsonify(error="Biometric storage unavailable"), 503

    if result["deleted_count"] == 0 and result["logs_deleted_count"] == 0:
        return jsonify(error="Participant not found"), 404

    return jsonify(ok=True, result=result), 200
