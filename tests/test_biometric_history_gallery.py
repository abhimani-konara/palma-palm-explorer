"""Isolated ICA02 history and gallery API tests - no real participant data."""

from contextlib import closing
import io
import secrets
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
from flask import Flask

import biometric_storage as storage
from biometric_api import biometric_bp


class BiometricHistoryGalleryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        db_patch = patch.object(storage, "DB_PATH", Path(temporary.name) / "test.sqlite3")
        db_patch.start()
        self.addCleanup(db_patch.stop)
        storage.initialize_database()

        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY=secrets.token_hex(32))
        app.register_blueprint(biometric_bp)
        self.client = app.test_client()
        self.login()
        self.headers = {"Origin": "http://localhost", "X-CSRF-Token": "unit-csrf"}

    def login(self):
        with self.client.session_transaction() as sess:
            sess["biometric_admin"] = True
            sess["admin_csrf_token"] = "unit-csrf"

    def insert_log(self, uid="TEST_A", outcome="Successful", score=0.9):
        with closing(sqlite3.connect(storage.DB_PATH)) as connection, connection:
            connection.execute(
                "INSERT INTO authentication_logs "
                "(user_id, timestamp, score, outcome, duration_ms) "
                "VALUES (?, ?, ?, ?, ?)",
                (uid, "2026-11-28T00:00:00+00:00", score, outcome, 12.5)
            )

    def test_history_requires_admin(self):
        with self.client.session_transaction() as sess:
            sess.clear()
        response = self.client.get("/api/biometric/history")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_history_refuses_nonlocal_request(self):
        response = self.client.get(
            "/api/biometric/history", environ_overrides={"REMOTE_ADDR": "192.0.2.1"}
        )
        self.assertEqual(response.status_code, 403)

    def test_history_shows_only_audit_metadata_and_caps_50(self):
        for i in range(54):
            self.insert_log(uid=f"TEST_{i}")
        response = self.client.get("/api/biometric/history")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["records"]), 50)
        self.assertEqual(response.json["records"][0]["user_id"], "TEST_53")
        self.assertEqual(
            set(response.json["records"][0]),
            {"attempt_id", "user_id", "timestamp", "score", "outcome", "duration_ms"},
        )
        self.assertNotIn("encrypted_templates", response.get_data(as_text=True))

    def test_history_filters_by_valid_participant(self):
        self.insert_log("TEST_A")
        self.insert_log("TEST_B")
        response = self.client.get("/api/biometric/history?user_id=TEST_A")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["count"], 1)
        self.assertEqual(response.json["records"][0]["user_id"], "TEST_A")

    def test_history_rejects_bad_participant_id(self):
        response = self.client.get("/api/biometric/history?user_id=TEST%20A")
        self.assertEqual(response.status_code, 400)

    @staticmethod
    def _image_bytes():
        pixels = np.full((260, 260, 3), 128, dtype=np.uint8)
        ok, encoded = cv2.imencode(".png", pixels)
        assert ok
        return encoded.tobytes()

    def _verify(self, include_stages=False):
        fields = {"user_id": "TEST_A", "image": (io.BytesIO(self._image_bytes()), "test.png")}
        if include_stages:
            fields["include_stages"] = "yes"
        return self.client.post(
            "/api/biometric/verify", data=fields,
            content_type="multipart/form-data", headers=self.headers,
        )

    def test_verified_gallery_is_opt_in_and_not_cached(self):
        with patch("biometric_api.load_enrollment", return_value={"hand_side": "right"}), \
             patch("biometric_api.verify_palm_image", return_value={
                 "status": "score_calculated", "average_score": 0.93}), \
             patch("biometric_api.save_authentication_log") as audit, \
             patch("biometric_visuals.render_processing_stages", return_value=[{
                 "title": "Grayscale", "data_url": "data:image/png;base64,ZmFrZQ=="
             }]) as render:
            response = self._verify(include_stages=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "Authentication Successful")
        self.assertEqual(response.json["threshold"], 0.90)
        self.assertEqual(len(response.json["stages"]), 1)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        audit.assert_called_once()
        render.assert_called_once()

    def test_no_stage_render_when_not_requested(self):
        with patch("biometric_api.load_enrollment", return_value={"hand_side": "right"}), \
             patch("biometric_api.verify_palm_image", return_value={
                 "status": "score_calculated", "average_score": 0.75}), \
             patch("biometric_api.save_authentication_log"), \
             patch("biometric_visuals.render_processing_stages") as render:
            response = self._verify()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "Authentication Failed")
        self.assertNotIn("stages", response.json)
        render.assert_not_called()

    def test_invalid_image_is_audited(self):
        with patch("biometric_api.load_enrollment", return_value={"hand_side": "right"}), \
             patch("biometric_api.verify_palm_image", return_value={
                 "status": "Invalid Image", "reasons": ["Blurred"]}), \
             patch("biometric_api.save_authentication_log") as audit:
            response = self._verify(include_stages=True)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json["status"], "Invalid Image")
        self.assertEqual(audit.call_args.args[1], "Invalid Image")

    def test_unknown_id_is_audited_as_failed(self):
        with patch("biometric_api.load_enrollment", return_value=None), \
             patch("biometric_api.save_authentication_log") as audit:
            response = self._verify()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "Authentication Failed")
        self.assertEqual(audit.call_args.args[1], "Failed")


if __name__ == "__main__":
    unittest.main()
