from contextlib import closing
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash

import biometric_storage as storage
from app import app


class BiometricStorageTests(unittest.TestCase):

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

        self.test_db = (
            Path(self.temporary.name) / "test_biometrics.sqlite3"
        )

        db_patch = patch.object(
            storage, "DB_PATH", self.test_db
        )
        db_patch.start()
        self.addCleanup(db_patch.stop)

        key_patch = patch.dict(
            os.environ,
            {
                "PALMA_BIOMETRIC_KEY":
                    Fernet.generate_key().decode("ascii")
            }
        )
        key_patch.start()
        self.addCleanup(key_patch.stop)

        self.enrollment = {
            "user_id": "UNITTEST01",
            "hand_side": "right",
            "templates": [
                {
                    "edge_features": [0.15 + i * 0.01] * 64,
                    "lbp_features": [0.002] * 256
                }
                for i in range(3)
            ]
        }

    def test_enrollment_encrypts_and_loads(self):
        result = storage.save_enrollment(self.enrollment)

        self.assertEqual(result["status"], "Enrollment Saved")
        self.assertEqual(result["template_count"], 3)

        loaded = storage.load_enrollment("UNITTEST01")

        self.assertEqual(loaded, self.enrollment)

    def test_database_does_not_store_plaintext_templates(self):
        storage.save_enrollment(self.enrollment)

        with closing(sqlite3.connect(self.test_db)) as connection:
            encrypted = connection.execute(
                "SELECT encrypted_templates FROM enrollments"
            ).fetchone()[0]

        self.assertIsInstance(encrypted, bytes)
        self.assertTrue(encrypted.startswith(b"gAAAA"))
        self.assertNotIn(b"edge_features", encrypted)
        self.assertNotIn(b"lbp_features", encrypted)

    def test_duplicate_enrollment_is_rejected(self):
        storage.save_enrollment(self.enrollment)

        with self.assertRaises(sqlite3.IntegrityError):
            storage.save_enrollment(self.enrollment)

        loaded = storage.load_enrollment("UNITTEST01")
        self.assertEqual(len(loaded["templates"]), 3)

    def test_invalid_template_is_rejected(self):
        invalid = {
            "user_id": "INVALID01",
            "hand_side": "right",
            "templates": [
                {"edge_features": [], "lbp_features": []}
            ] * 3
        }

        with self.assertRaises(ValueError):
            storage.save_enrollment(invalid)

    def test_missing_encryption_key_is_rejected(self):
        with patch.dict(
            os.environ,
            {"PALMA_BIOMETRIC_KEY": ""}
        ):
            with self.assertRaises(RuntimeError):
                storage.save_enrollment(self.enrollment)


class BiometricAdminLoginTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.password = "unit-test-only-password-123"

    def get_csrf(self):
        response = self.client.get(
            "/api/biometric/admin/session"
        )
        self.assertEqual(response.status_code, 200)
        return response.json["csrf_token"]

    def test_correct_admin_password(self):
        csrf = self.get_csrf()

        with patch.dict(
            os.environ,
            {
                "PALMA_ADMIN_PASSWORD_HASH":
                    generate_password_hash(self.password)
            }
        ):
            response = self.client.post(
                "/api/biometric/admin/login",
                json={"password": self.password},
                headers={
                    "Origin": "http://localhost",
                    "X-CSRF-Token": csrf
                }
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["authenticated"])

        session_response = self.client.get(
            "/api/biometric/admin/session"
        )
        self.assertTrue(
            session_response.json["authenticated"]
        )

    def test_wrong_admin_password(self):
        csrf = self.get_csrf()

        with patch.dict(
            os.environ,
            {
                "PALMA_ADMIN_PASSWORD_HASH":
                    generate_password_hash(self.password)
            }
        ):
            response = self.client.post(
                "/api/biometric/admin/login",
                json={"password": "incorrect-test-password"},
                headers={
                    "Origin": "http://localhost",
                    "X-CSRF-Token": csrf
                }
            )

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main(verbosity=2)
