
import os
import sqlite3
from pathlib import Path
from cryptography.fernet import Fernet


# Local SQLite database file
DB_PATH = Path(__file__).parent / "biometric_data.sqlite3"


def get_cipher():
    """Load the secret encryption key."""

    key = os.environ.get("PALMA_BIOMETRIC_KEY")

    if not key:
        raise RuntimeError(
            "PALMA_BIOMETRIC_KEY is not configured"
        )

    return Fernet(key.encode("ascii"))


def initialize_database():
    """Create database tables if they do not exist."""

    with sqlite3.connect(DB_PATH) as connection:

        # Registered palm biometric templates
        connection.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                user_id TEXT PRIMARY KEY,
                hand_side TEXT NOT NULL,
                encrypted_templates BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Authentication attempt history
        connection.execute("""
            CREATE TABLE IF NOT EXISTS authentication_logs (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                score REAL,
                outcome TEXT NOT NULL,
                duration_ms REAL
            )
        """)

    return True

def save_enrollment(enrollment):
    """Encrypt and store three biometric templates."""

    import json
    from datetime import datetime, timezone

    if not isinstance(enrollment, dict):
        raise ValueError("Invalid enrollment data")

    user_id = str(enrollment.get("user_id", "")).strip()
    hand_side = enrollment.get("hand_side")
    templates = enrollment.get("templates")

    if not user_id:
        raise ValueError("User ID is required")

    if hand_side not in ("left", "right"):
        raise ValueError("Invalid hand side")

    if not isinstance(templates, list) or len(templates) != 3:
        raise ValueError("Exactly three templates are required")

    for template in templates:
        if not isinstance(template, dict):
            raise ValueError("Invalid biometric template")

        if (
            len(template.get("edge_features", [])) != 64
            or len(template.get("lbp_features", [])) != 256
        ):
            raise ValueError("Incorrect biometric feature count")

    cipher = get_cipher()

    template_data = json.dumps(templates).encode("utf-8")
    encrypted_data = cipher.encrypt(template_data)

    created_at = datetime.now(timezone.utc).isoformat()

    initialize_database()

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            INSERT INTO enrollments
                (user_id, hand_side, encrypted_templates, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            hand_side,
            encrypted_data,
            created_at
        ))

    return {
        "status": "Enrollment Saved",
        "user_id": user_id,
        "hand_side": hand_side,
        "template_count": len(templates)
    }

def load_enrollment(user_id):
    """Load and decrypt an enrolled user's biometric templates."""

    import json

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Valid User ID is required")

    initialize_database()

    with sqlite3.connect(DB_PATH) as connection:
        record = connection.execute(
            """
            SELECT hand_side, encrypted_templates
            FROM enrollments
            WHERE user_id = ?
            """,
            (user_id.strip(),)
        ).fetchone()

    if record is None:
        return None

    hand_side, encrypted_data = record

    cipher = get_cipher()
    decrypted_data = cipher.decrypt(encrypted_data)

    templates = json.loads(decrypted_data.decode("utf-8"))

    return {
        "user_id": user_id.strip(),
        "hand_side": hand_side,
        "templates": templates
    }

def save_authentication_log(user_id, outcome, score=None, duration_ms=None):
    """Save one biometric authentication attempt."""

    from datetime import datetime, timezone
    import math

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Valid User ID is required")

    allowed_outcomes = (
        "Successful",
        "Failed",
        "Invalid Image",
        "Calibration Required"
    )

    if outcome not in allowed_outcomes:
        raise ValueError("Invalid authentication outcome")

    if score is not None:
        score = float(score)
        if not math.isfinite(score) or not 0.0 <= score <= 1.0:
            raise ValueError("Score must be between 0 and 1")

    if duration_ms is not None:
        duration_ms = float(duration_ms)
        if not math.isfinite(duration_ms) or duration_ms < 0:
            raise ValueError("Invalid duration")

    timestamp = datetime.now(timezone.utc).isoformat()

    initialize_database()

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            INSERT INTO authentication_logs
                (user_id, timestamp, score, outcome, duration_ms)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id.strip(),
                timestamp,
                score,
                outcome,
                duration_ms
            )
        )

        attempt_id = cursor.lastrowid

    return {
        "status": "Log Saved",
        "attempt_id": attempt_id,
        "outcome": outcome
    }

def get_authentication_logs(user_id):
    """Retrieve authentication history for one user."""

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Valid User ID is required")

    initialize_database()

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT attempt_id, timestamp, score,
                   outcome, duration_ms
            FROM authentication_logs
            WHERE user_id = ?
            ORDER BY attempt_id DESC
            """,
            (user_id.strip(),)
        ).fetchall()

    return [dict(row) for row in rows]

def delete_enrollment(user_id):
    """Delete one user's stored biometric enrollment."""

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Valid User ID is required")

    initialize_database()

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            "DELETE FROM enrollments WHERE user_id = ?",
            (user_id.strip(),)
        )

        deleted_count = cursor.rowcount

    return {
        "status": "Enrollment Deleted" if deleted_count else "Not Found",
        "user_id": user_id.strip(),
        "deleted_count": deleted_count
    }
