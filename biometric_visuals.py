"""In-memory ICA02 processing views for an authorized verification request.

Views are PNG data URIs returned only to the local authenticated admin. No files
or images are saved. These are genuine stages of the verification pipeline.
"""

import base64

import cv2
import numpy as np
import mediapipe as mp

from biometric import (
    extract_palm_roi,
    extract_edge_features,
    extract_lbp_features,
    preprocess_palm_roi,
)


def _preview(image, max_side=512):
    height, width = image.shape[:2]
    scale = min(1.0, max_side / max(width, height))
    if scale < 1:
        return cv2.resize(
            image,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
    return image.copy()


def _png_data_url(image):
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise ValueError("Image preview encoding failed")
    return "data:image/png;base64," + base64.b64encode(encoded).decode("ascii")


def _landmark_preview(image):
    """Draw observed MediaPipe wrist and finger-base references 0, 5, 17."""
    preview = _preview(image)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with mp.solutions.hands.Hands(
        static_image_mode=True,
        max_num_hands=1,
        min_detection_confidence=0.5,
    ) as detector:
        result = detector.process(rgb)

    if not result.multi_hand_landmarks:
        raise ValueError("Hand landmarks unavailable")

    landmarks = result.multi_hand_landmarks[0].landmark
    height, width = preview.shape[:2]
    refs = [(0, (30, 255, 245)), (5, (90, 215, 90)), (17, (245, 190, 90))]
    pts = {}
    for idx, color in refs:
        x = int(np.clip(landmarks[idx].x * width, 0, width - 1))
        y = int(np.clip(landmarks[idx].y * height, 0, height - 1))
        pts[idx] = (x, y)
        cv2.circle(preview, (x, y), 6, color, -1)
        cv2.putText(preview, str(idx), (x + 8, max(12, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
    cv2.line(preview, pts[5], pts[17], (255, 210, 140), 2)
    cv2.line(preview, pts[0], pts[5], (255, 210, 140), 2)
    cv2.line(preview, pts[0], pts[17], (255, 210, 140), 2)
    return preview


def render_processing_stages(image):
    """Render actual ROI, grayscale, denoise, CLAHE, Canny and LBP stages."""
    roi = extract_palm_roi(image)
    if roi is None:
        raise ValueError("Palm ROI unavailable")

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (256, 256))
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    enhanced = preprocess_palm_roi(roi)
    _, edges = extract_edge_features(enhanced)
    _, lbp = extract_lbp_features(enhanced)

    stages = [
        ("Uploaded palm (resized preview)", _preview(image)),
        ("Observed landmark references: 0, 5, 17", _landmark_preview(image)),
        ("Aligned palm ROI (256 x 256)", roi),
        ("Grayscale", gray),
        ("Gaussian denoising", blurred),
        ("CLAHE contrast enhancement", enhanced),
        ("Canny edges (60, 140)", edges),
        ("Local Binary Pattern texture", lbp),
    ]
    return [{"title": title, "data_url": _png_data_url(stage)}
            for title, stage in stages]
