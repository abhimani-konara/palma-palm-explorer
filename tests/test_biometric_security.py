import os
import unittest
from unittest.mock import patch

from app import app


class BiometricSecurityTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.csrf = "local-unit-test-csrf"
        self.origin = "http://localhost"

    def login_test_session(self):
        with self.client.session_transaction() as session:
            session["biometric_admin"] = True
            session["admin_csrf_token"] = self.csrf

    def secure_headers(self):
        return {
            "Origin": self.origin,
            "X-CSRF-Token": self.csrf
        }

    def test_admin_session_starts_unauthenticated(self):
        response = self.client.get(
            "/api/biometric/admin/session"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json["authenticated"])
        self.assertTrue(response.json["csrf_token"])

    def test_admin_login_requires_csrf(self):
        self.client.get("/api/biometric/admin/session")
        response = self.client.post(
            "/api/biometric/admin/login",
            json={"password": "invalid-test-password"}
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_logout_requires_csrf(self):
        self.login_test_session()
        response = self.client.post(
            "/api/biometric/admin/logout"
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_rejects_remote_access(self):
        response = self.client.get(
            "/api/biometric/admin/session",
            environ_overrides={
                "REMOTE_ADDR": "203.0.113.42"
            }
        )
        self.assertEqual(response.status_code, 403)

    def test_enrollment_requires_admin(self):
        response = self.client.post(
            "/api/biometric/enroll",
            headers={"Origin": self.origin},
            data={}
        )
        self.assertEqual(response.status_code, 401)

    def test_enrollment_requires_csrf(self):
        self.login_test_session()
        response = self.client.post(
            "/api/biometric/enroll",
            headers={"Origin": self.origin},
            data={}
        )
        self.assertEqual(response.status_code, 403)

    def test_enrollment_rejects_invalid_id(self):
        self.login_test_session()
        response = self.client.post(
            "/api/biometric/enroll",
            headers=self.secure_headers(),
            data={"user_id": "bad id"}
        )
        self.assertEqual(response.status_code, 400)

    def test_enrollment_requires_consent(self):
        self.login_test_session()
        response = self.client.post(
            "/api/biometric/enroll",
            headers=self.secure_headers(),
            data={
                "user_id": "UNITTEST01",
                "hand_side": "right"
            }
        )
        self.assertEqual(response.status_code, 400)

    def test_enrollment_requires_three_images(self):
        self.login_test_session()
        response = self.client.post(
            "/api/biometric/enroll",
            headers=self.secure_headers(),
            data={
                "user_id": "UNITTEST01",
                "hand_side": "right",
                "consent": "true"
            }
        )
        self.assertEqual(response.status_code, 400)

    def test_verification_requires_authorization(self):
        with patch.dict(
            os.environ,
            {"PALMA_BIOMETRIC_API_TOKEN": "unit-test-token"}
        ):
            response = self.client.post(
                "/api/biometric/verify",
                data={}
            )
        self.assertEqual(response.status_code, 401)

    def test_verification_requires_csrf(self):
        self.login_test_session()
        response = self.client.post(
            "/api/biometric/verify",
            headers={"Origin": self.origin},
            data={}
        )
        self.assertEqual(response.status_code, 403)

    def test_verification_rejects_invalid_id(self):
        self.login_test_session()
        response = self.client.post(
            "/api/biometric/verify",
            headers=self.secure_headers(),
            data={"user_id": "invalid id"}
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
