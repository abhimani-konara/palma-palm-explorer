
import cv2
import numpy as np
import mediapipe as mp


def extract_palm_roi(image):
    """Extract a normalized palm region using hand landmarks."""

    if image is None or image.size == 0:
        return None

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with mp.solutions.hands.Hands(
        static_image_mode=True,
        max_num_hands=1,
        min_detection_confidence=0.5
    ) as hands:
        result = hands.process(rgb)

    if not result.multi_hand_landmarks:
        return None

    height, width = image.shape[:2]
    landmarks = result.multi_hand_landmarks[0].landmark

    def point(index):
        return np.array([
            landmarks[index].x * width,
            landmarks[index].y * height
        ], dtype=np.float32)

    wrist = point(0)
    index_base = point(5)
    pinky_base = point(17)

    palm_width = pinky_base - index_base
    top_middle = (index_base + pinky_base) / 2
    bottom_middle = wrist * 0.75 + top_middle * 0.25

    corners = np.float32([
        index_base + palm_width * 0.12,
        pinky_base - palm_width * 0.12,
        bottom_middle + palm_width * 0.36,
        bottom_middle - palm_width * 0.36
    ])

    destination = np.float32([
        [0, 0],
        [255, 0],
        [255, 255],
        [0, 255]
    ])

    matrix = cv2.getPerspectiveTransform(
        corners, destination
    )

    roi = cv2.warpPerspective(
        image, matrix, (256, 256)
    )

    return roi

def preprocess_palm_roi(roi):
    """Prepare palm ROI for biometric feature extraction."""

    if roi is None or roi.size == 0:
        return None

    # Step 1: Convert to grayscale
    if len(roi.shape) == 3:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    else:
        gray = roi.copy()

    # Step 2: Normalize image size
    gray = cv2.resize(gray, (256, 256))

    # Step 3: Reduce image noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Step 4: Improve local contrast
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(blurred)

    return enhanced

def extract_edge_features(preprocessed):
    """Extract Canny edge features from a palm ROI."""

    if preprocessed is None or preprocessed.ndim != 2:
        raise ValueError("A grayscale palm image is required")

    # Detect image edges
    edges = cv2.Canny(preprocessed, 60, 140)

    # Divide the image into an 8 x 8 grid
    features = []

    for row in np.array_split(edges, 8, axis=0):
        for block in np.array_split(row, 8, axis=1):

            # Calculate the fraction of edge pixels
            edge_density = np.count_nonzero(block) / block.size

            features.append(edge_density)

    # Convert values into a numerical feature vector
    features = np.array(features, dtype=np.float32)

    return features, edges

def extract_lbp_features(preprocessed):
    """Extract Local Binary Pattern texture features."""

    if preprocessed is None or preprocessed.ndim != 2:
        raise ValueError("A grayscale palm image is required")

    # Center pixels (ignore the outer 1-pixel border)
    center = preprocessed[1:-1, 1:-1]

    # Eight neighboring pixels
    neighbors = [
        preprocessed[:-2, :-2],
        preprocessed[:-2, 1:-1],
        preprocessed[:-2, 2:],
        preprocessed[1:-1, 2:],
        preprocessed[2:, 2:],
        preprocessed[2:, 1:-1],
        preprocessed[2:, :-2],
        preprocessed[1:-1, :-2]
    ]

    # Calculate the 8-bit LBP code
    lbp = np.zeros_like(center, dtype=np.uint8)

    for i, neighbor in enumerate(neighbors):
        binary = (neighbor >= center).astype(np.uint8)
        lbp |= binary << (7 - i)

    # Count the occurrence of all 256 LBP patterns
    features = np.bincount(
        lbp.ravel(), minlength=256
    ).astype(np.float32)

    # Normalize the feature vector
    features /= max(features.sum(), 1.0)

    return features, lbp

def create_biometric_template(preprocessed):
    """Create a numerical template from a preprocessed palm ROI."""

    if preprocessed is None or preprocessed.ndim != 2:
        raise ValueError("A preprocessed grayscale ROI is required")

    # Method 1: Edge features
    edge_features, _ = extract_edge_features(preprocessed)

    # Method 2: Texture features
    lbp_features, _ = extract_lbp_features(preprocessed)

    # Keep both feature types separately
    template = {
        "version": 1,
        "edge_features": edge_features.tolist(),
        "lbp_features": lbp_features.tolist()
    }

    return template

def prepare_enrollment(user_id, hand_side, image_paths, consent=False):
    """Prepare three palm templates for one user."""

    if not consent:
        raise ValueError("User consent is required")

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("User ID is required")

    hand_side = hand_side.strip().lower()

    if hand_side not in ("left", "right"):
        raise ValueError("Hand side must be left or right")

    if len(image_paths) != 3:
        raise ValueError("Exactly 3 palm images are required")

    if len(set(image_paths)) != 3:
        raise ValueError("Choose 3 different image files")

    enrollment = {
        "user_id": user_id.strip(),
        "hand_side": hand_side,
        "templates": []
    }

    for number, path in enumerate(image_paths, start=1):
        image = cv2.imread(path)

        if image is None:
            raise ValueError(
                f"Image {number} could not be opened"
            )

        quality = check_palm_image_quality(image)

        if not quality["valid"]:
            reasons = ", ".join(quality["reasons"])
            raise ValueError(
                f"Image {number} failed quality check: {reasons}"
            )

        detected = detect_hand_side(image, mirrored=False)

        if detected["hand_side"] is None:
            raise ValueError(
                f"Image {number}: Hand side could not be detected"
            )

        if detected["confidence"] < 0.80:
            raise ValueError(
                f"Image {number}: Hand-side confidence is too low"
            )

        if detected["hand_side"] != hand_side:
            raise ValueError(
                f"Image {number}: Expected {hand_side} hand, "
                f"but detected {detected['hand_side']} hand"
            )


        roi = extract_palm_roi(image)

        if roi is None:
            raise ValueError(
                f"No hand detected in image {number}"
            )

        processed = preprocess_palm_roi(roi)
        template = create_biometric_template(processed)

        enrollment["templates"].append(template)

    return enrollment

def compare_biometric_templates(template1, template2):
    """Compare two palm biometric templates."""

    if template1.get("version") != 1 or template2.get("version") != 1:
        raise ValueError("Unsupported template version")

    # Method 1: Compare Canny edge features
    edge1 = np.asarray(template1["edge_features"], dtype=np.float64)
    edge2 = np.asarray(template2["edge_features"], dtype=np.float64)

    # Method 2: Compare LBP texture features
    lbp1 = np.asarray(template1["lbp_features"], dtype=np.float64)
    lbp2 = np.asarray(template2["lbp_features"], dtype=np.float64)

    if edge1.shape != (64,) or edge2.shape != (64,):
        raise ValueError("Invalid edge feature length")

    if lbp1.shape != (256,) or lbp2.shape != (256,):
        raise ValueError("Invalid LBP feature length")

    for values in (edge1, edge2, lbp1, lbp2):
        if not np.all(np.isfinite(values)):
            raise ValueError("Feature values must be finite")
        if np.any(values < 0):
            raise ValueError("Negative feature values are invalid")

    # Cosine similarity for edge patterns
    norm1 = np.linalg.norm(edge1)
    norm2 = np.linalg.norm(edge2)

    if norm1 == 0 or norm2 == 0:
        edge_score = 0.0
    else:
        edge_score = float(
            np.dot(edge1, edge2) / (norm1 * norm2)
        )

    # Histogram intersection for LBP patterns
    if lbp1.sum() <= 0 or lbp2.sum() <= 0:
        raise ValueError("Empty LBP histogram")

    lbp1 = lbp1 / lbp1.sum()
    lbp2 = lbp2 / lbp2.sum()

    texture_score = float(np.minimum(lbp1, lbp2).sum())

    # Combine both methods (initial experimental weights)
    combined_score = (
        0.5 * edge_score +
        0.5 * texture_score
    )

    return {
        "edge_score": round(float(np.clip(edge_score, 0, 1)), 4),
        "texture_score": round(float(np.clip(texture_score, 0, 1)), 4),
        "combined_score": round(float(np.clip(combined_score, 0, 1)), 4)
    }

def calculate_verification_score(
    enrollment,
    new_template,
    hand_side
):
    """Compare a new palm template with enrolled templates."""

    if not isinstance(enrollment, dict):
        raise ValueError("Invalid enrollment data")

    enrolled_side = enrollment.get("hand_side")

    if not isinstance(hand_side, str):
        raise ValueError("Hand side is required")

    if hand_side.strip().lower() != enrolled_side:
        raise ValueError("Hand side does not match enrollment")

    templates = enrollment.get("templates", [])

    if len(templates) != 3:
        raise ValueError("Three enrollment templates are required")

    scores = []

    for enrolled_template in templates:
        result = compare_biometric_templates(
            enrolled_template,
            new_template
        )

        scores.append(result["combined_score"])

    average_score = float(np.mean(scores))

    return {
        "user_id": enrollment["user_id"],
        "hand_side": enrolled_side,
        "individual_scores": scores,
        "average_score": round(average_score, 4),
        "status": "score_calculated"
    }

def make_authentication_decision(score_result, threshold=None):
    """Make an authentication decision using a calibrated threshold."""

    if not isinstance(score_result, dict):
        raise ValueError("Invalid verification result")

    score = score_result.get("average_score")

    if score is None or not np.isfinite(score):
        return {
            "status": "Invalid Image",
            "score": None
        }

    score = float(score)

    if not 0 <= score <= 1:
        raise ValueError("Score must be between 0 and 1")

    # A real threshold must be obtained from validation data
    if threshold is None:
        return {
            "status": "Calibration Required",
            "score": score
        }

    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Invalid threshold")

    if score >= threshold:
        status = "Authentication Successful"
    else:
        status = "Authentication Failed"

    return {
        "status": status,
        "score": score,
        "threshold": float(threshold)
    }

def check_palm_image_quality(image):
    """Check basic image quality before biometric processing."""

    if image is None or image.size == 0:
        return {
            "valid": False,
            "reasons": ["Image could not be loaded"],
            "metrics": {}
        }

    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif image.ndim == 2:
        gray = image
    else:
        raise ValueError("Unsupported image format")

    height, width = gray.shape

    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    sharpness = float(
        cv2.Laplacian(gray, cv2.CV_64F).var()
    )

    reasons = []

    # Minimum image resolution
    if min(height, width) < 256:
        reasons.append("Image resolution is too low")

    # Exposure checking
    if brightness < 45:
        reasons.append("Image is too dark")
    elif brightness > 215:
        reasons.append("Image is too bright")

    # Contrast checking
    if contrast < 18:
        reasons.append("Image contrast is too low")

    # Blur checking

    # Check palm ROI when full-image sharpness is low
    if sharpness < 30:
        roi = extract_palm_roi(image)

        if roi is None:
            reasons.append("Palm ROI could not be detected")
        else:
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            roi_sharpness = cv2.Laplacian(
                roi_gray, cv2.CV_64F
            ).var()

            if roi_sharpness < 30:
                reasons.append("Palm ROI may be too blurry")


    return {
        "valid": len(reasons) == 0,
        "reasons": reasons,
        "metrics": {
            "width": width,
            "height": height,
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "sharpness": round(sharpness, 2)
        }
    }

def verify_palm_image(enrollment, image, hand_side):
    """Check image quality and calculate biometric matching score."""

    # Step 1: Check image quality
    quality = check_palm_image_quality(image)

    if not quality["valid"]:
        return {
            "status": "Invalid Image",
            "reasons": quality["reasons"]
        }

    # Check enrollment hand side
    if not isinstance(enrollment, dict):
        return {
            "status": "Invalid Enrollment",
            "reasons": ["Enrollment data is missing"]
        }

    expected_side = enrollment.get("hand_side")

    if expected_side not in ("left", "right"):
        return {
            "status": "Invalid Enrollment",
            "reasons": ["Invalid enrolled hand side"]
        }

    if not isinstance(hand_side, str) or hand_side.strip().lower() != expected_side:
        return {
            "status": "Invalid Image",
            "reasons": ["Selected hand side does not match enrollment"]
        }

    # Detect the actual hand side
    detected = detect_hand_side(image, mirrored=False)

    if detected["hand_side"] is None or detected["confidence"] < 0.80:
        return {
            "status": "Invalid Image",
            "reasons": ["Hand side could not be reliably detected"]
        }

    if detected["hand_side"] != expected_side:
        return {
            "status": "Invalid Image",
            "reasons": ["Wrong hand uploaded"]
        }

    # Step 2: Detect hand and extract palm ROI
    roi = extract_palm_roi(image)

    if roi is None:
        return {
            "status": "Invalid Image",
            "reasons": ["No palm detected"]
        }

    # Step 3: Preprocess the extracted palm
    processed = preprocess_palm_roi(roi)

    # Step 4: Extract biometric features
    new_template = create_biometric_template(processed)

    # Step 5: Compare with enrolled templates
    result = calculate_verification_score(
        enrollment,
        new_template,
        hand_side
    )

    return result

def detect_hand_side(image, mirrored=False):
    """Estimate whether the image contains a left or right hand."""

    if image is None or image.size == 0:
        return {
            "hand_side": None,
            "confidence": 0.0
        }

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with mp.solutions.hands.Hands(
        static_image_mode=True,
        max_num_hands=1,
        min_detection_confidence=0.5
    ) as hands:
        result = hands.process(rgb)

    if not result.multi_handedness:
        return {
            "hand_side": None,
            "confidence": 0.0
        }

    classification = (
        result.multi_handedness[0].classification[0]
    )

    detected_side = classification.label.lower()

    # MediaPipe Hands assumes mirrored (selfie) input.
    # Swap its label for a normal, non-mirrored photo.
    if not mirrored:
        detected_side = (
            "left" if detected_side == "right" else "right"
        )

    return {
        "hand_side": detected_side,
        "confidence": round(
            float(classification.score), 3
        )
    }
