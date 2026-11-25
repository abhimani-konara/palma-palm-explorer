from pathlib import Path
import cv2

from biometric_storage import load_enrollment
from biometric import (
    verify_palm_image,
    extract_palm_roi,
    preprocess_palm_roi,
    create_biometric_template,
    calculate_verification_score
)

THRESHOLD = 0.90

USER_IDS = [
    "P-A", "P-B", "P-F",
    "P-G", "P-H", "P-I",
    "P-J", "P-K", "P-P"
]

DATASET = Path.home() / "Downloads/participants/participants"

enrollments = {}

for user_id in USER_IDS:
    enrollment = load_enrollment(user_id)

    if enrollment is None:
        raise ValueError(f"Missing enrollment: {user_id}")

    enrollments[user_id] = enrollment


genuine_total = 0
impostor_total = 0
false_rejects = 0
false_accepts = 0
invalid_images = []

print("PALMA - Test Set Evaluation")
print("Threshold:", THRESHOLD)
print("Testing images: 5.jpg")
print("-" * 45)

for query_id in USER_IDS:

    path = DATASET / query_id / "5.jpg"
    image = cv2.imread(str(path))

    if image is None:
        print(query_id, "- IMAGE NOT FOUND")
        invalid_images.append(query_id)
        continue

    genuine = verify_palm_image(
        enrollments[query_id], image, "right"
    )

    if genuine.get("status") != "score_calculated":
        print(query_id, "- INVALID IMAGE")
        invalid_images.append(query_id)
        continue

    roi = extract_palm_roi(image)

    if roi is None:
        print(query_id, "- ROI FAILED")
        invalid_images.append(query_id)
        continue

    processed = preprocess_palm_roi(roi)
    query_template = create_biometric_template(processed)

    genuine_score = genuine["average_score"]
    genuine_total += 1

    if genuine_score < THRESHOLD:
        false_rejects += 1
        genuine_result = "REJECT"
    else:
        genuine_result = "ACCEPT"

    for claimed_id in USER_IDS:

        if claimed_id == query_id:
            continue

        result = calculate_verification_score(
            enrollments[claimed_id],
            query_template,
            "right"
        )

        if result.get("status") != "score_calculated":
            raise ValueError(
                f"Comparison failed: {query_id} -> {claimed_id}"
            )

        impostor_total += 1

        if result["average_score"] >= THRESHOLD:
            false_accepts += 1

    print(
        f"{query_id} | Genuine score: {genuine_score:.4f} "
        f"| {genuine_result}"
    )


print("-" * 45)
print("Valid genuine attempts:", genuine_total)
print("Valid impostor attempts:", impostor_total)
print("Invalid images:", invalid_images)

print("False rejects:", false_rejects)
print("False accepts:", false_accepts)

if genuine_total > 0 and impostor_total > 0:

    frr = false_rejects / genuine_total * 100
    far = false_accepts / impostor_total * 100

    print("FRR:", round(frr, 2), "%")
    print("FAR:", round(far, 2), "%")

print("-" * 45)
print("Test set evaluation completed")
