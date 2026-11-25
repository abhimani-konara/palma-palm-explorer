from pathlib import Path
from statistics import mean
import cv2

from biometric_storage import load_enrollment
from biometric import (
    verify_palm_image,
    extract_palm_roi,
    preprocess_palm_roi,
    create_biometric_template,
    calculate_verification_score
)

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

genuine_scores = []
impostor_scores = []
skipped = []

print("PALMA - Validation using 4.jpg")
print("-" * 45)

for query_id in USER_IDS:
    image_path = DATASET / query_id / "4.jpg"
    image = cv2.imread(str(image_path))

    if image is None:
        print(query_id, "- IMAGE NOT FOUND")
        skipped.append(query_id)
        continue

    # Check image quality and hand side
    own_result = verify_palm_image(
        enrollments[query_id], image, "right"
    )

    if own_result.get("status") != "score_calculated":
        print(query_id, "- INVALID IMAGE:", own_result)
        skipped.append(query_id)
        continue

    roi = extract_palm_roi(image)

    if roi is None:
        print(query_id, "- ROI FAILED")
        skipped.append(query_id)
        continue

    processed = preprocess_palm_roi(roi)
    query_template = create_biometric_template(processed)

    genuine_score = own_result["average_score"]
    genuine_scores.append(genuine_score)

    person_impostor_scores = []

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

        score = result["average_score"]
        impostor_scores.append(score)
        person_impostor_scores.append(score)

    print(
        f"{query_id} | Genuine: {genuine_score:.4f} | "
        f"Highest impostor: {max(person_impostor_scores):.4f}"
    )

print("-" * 45)

print("Genuine attempts:", len(genuine_scores))
print("Impostor attempts:", len(impostor_scores))
print("Skipped participants:", skipped)

if genuine_scores and impostor_scores:
    print("Genuine average:", round(mean(genuine_scores), 4))
    print("Impostor average:", round(mean(impostor_scores), 4))

    print("\nValidation Threshold Comparison")

    for threshold in (0.84, 0.86, 0.87, 0.88, 0.90):
        false_rejects = sum(
            score < threshold for score in genuine_scores
        )
        false_accepts = sum(
            score >= threshold for score in impostor_scores
        )

        print(
            f"Threshold {threshold:.2f} | "
            f"Genuine rejected: {false_rejects}/{len(genuine_scores)} | "
            f"Impostor accepted: {false_accepts}/{len(impostor_scores)}"
        )

print("-" * 45)
print("Validation completed")
