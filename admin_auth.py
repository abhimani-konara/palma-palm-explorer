
import os
import secrets
import time
from collections import defaultdict, deque
from threading import Lock

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

admin_bp = Blueprint(
    "palma_admin",
    __name__,
    url_prefix="/api/biometric/admin"
)

attempts = defaultdict(deque)
attempt_lock = Lock()
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 900


@admin_bp.before_request
def protect_admin_routes():
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify(error="Local access only"), 403

    if request.method == "POST":
        origin = request.headers.get("Origin")

        if origin and origin != request.host_url.rstrip("/"):
            return jsonify(error="Invalid request origin"), 403

        expected = session.get("admin_csrf_token")
        supplied = request.headers.get("X-CSRF-Token", "")

        if (
            not isinstance(expected, str)
            or not secrets.compare_digest(supplied, expected)
        ):
            return jsonify(error="Invalid security token"), 403


@admin_bp.after_request
def prevent_caching(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@admin_bp.get("/session")
def admin_session():
    session.permanent = True

    if not session.get("admin_csrf_token"):
        session["admin_csrf_token"] = secrets.token_urlsafe(32)

    return jsonify(
        authenticated=session.get("biometric_admin") is True,
        csrf_token=session["admin_csrf_token"]
    )


@admin_bp.post("/login")
def admin_login():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    if not isinstance(password, str) or not 1 <= len(password) <= 256:
        return jsonify(error="Invalid password input"), 400

    stored_hash = os.getenv("PALMA_ADMIN_PASSWORD_HASH")

    if not stored_hash:
        return jsonify(error="Admin login is not configured"), 503

    client = request.remote_addr
    now = time.monotonic()

    with attempt_lock:
        recent = attempts[client]

        while recent and now - recent[0] > WINDOW_SECONDS:
            recent.popleft()

        if len(recent) >= MAX_ATTEMPTS:
            return jsonify(error="Too many login attempts"), 429

        recent.append(now)

    if not check_password_hash(stored_hash, password):
        return jsonify(error="Incorrect password"), 401

    with attempt_lock:
        attempts[client].clear()

    session.clear()
    session.permanent = True
    session["biometric_admin"] = True
    session["admin_csrf_token"] = secrets.token_urlsafe(32)

    return jsonify(
        authenticated=True,
        csrf_token=session["admin_csrf_token"]
    )


@admin_bp.post("/logout")
def admin_logout():
    session.clear()
    return jsonify(authenticated=False)
