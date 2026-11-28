import secrets
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from flask import Flask
import biometric_storage as storage
from biometric_enrollment_api import enrollment_bp


class BiometricDeleteApiTests(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

        db_path = Path(self.folder.name) / "test.sqlite3"
        self.db_patch = patch.object(storage, "DB_PATH", db_path)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)

        storage.initialize_database()

        with closing(sqlite3.connect(db_path)) as db, db:
            for uid in ("TEST_A", "TEST_B"):
                db.execute(
                    "INSERT INTO enrollments VALUES (?, ?, ?, ?)",
                    (uid, "right", b"fake", "2026-11-28")
                )
                db.execute(
                    "INSERT INTO authentication_logs "
                    "(user_id, timestamp, outcome) VALUES (?, ?, ?)",
                    (uid, "2026-11-28", "Test")
                )

        app = Flask(__name__)
        app.config.update(
            TESTING=True,
            SECRET_KEY=secrets.token_hex(32)
        )
        app.register_blueprint(enrollment_bp)

        self.client = app.test_client()
        self.url = "/api/biometric/delete-enrollment"
        self.headers = {
            "Origin": "http://localhost",
            "X-CSRF-Token": "test-csrf-token"
        }
        self.data = {
            "user_id": "TEST_A",
            "confirm_user_id": "TEST_A"
        }

    def login_admin(self):
        with self.client.session_transaction() as sess:
            sess["biometric_admin"] = True
            sess["admin_csrf_token"] = "test-csrf-token"

    def request_delete(self, data=None, headers=None, **kwargs):
        return self.client.post(
            self.url,
            json=self.data if data is None else data,
            headers=self.headers if headers is None else headers,
            **kwargs
        )

    def test_admin_login_required(self):
        self.assertEqual(self.request_delete().status_code, 401)

    def test_invalid_csrf_rejected(self):
        self.login_admin()
        headers = dict(self.headers)
        headers["X-CSRF-Token"] = "wrong-token"
        self.assertEqual(
            self.request_delete(headers=headers).status_code, 403
        )

    def test_invalid_origin_rejected(self):
        self.login_admin()
        headers = dict(self.headers)
        headers["Origin"] = "http://example.com"
        self.assertEqual(
            self.request_delete(headers=headers).status_code, 403
        )

    def test_nonlocal_request_rejected(self):
        self.login_admin()
        response = self.request_delete(
            environ_overrides={"REMOTE_ADDR": "192.0.2.1"}
        )
        self.assertEqual(response.status_code, 403)

    def test_participant_confirmation_required(self):
        self.login_admin()
        data = {
            "user_id": "TEST_A",
            "confirm_user_id": "WRONG"
        }
        self.assertEqual(
            self.request_delete(data=data).status_code, 400
        )

    def test_authorized_deletion_preserves_other_user(self):
        self.login_admin()
        response = self.request_delete()
        self.assertEqual(response.status_code, 200)

        with closing(sqlite3.connect(storage.DB_PATH)) as db:
            for table in ("enrollments", "authentication_logs"):
                a = db.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE user_id = ?",
                    ("TEST_A",)
                ).fetchone()[0]
                b = db.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE user_id = ?",
                    ("TEST_B",)
                ).fetchone()[0]

                self.assertEqual(a, 0)
                self.assertEqual(b, 1)

    def test_unknown_participant_returns_404(self):
        self.login_admin()
        response = self.request_delete(data={
            "user_id": "UNKNOWN",
            "confirm_user_id": "UNKNOWN"
        })
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
