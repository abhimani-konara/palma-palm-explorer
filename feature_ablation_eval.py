import time
from pathlib import Path
from statistics import mean

import cv2

from biometric_storage import load_enrollment
from biometric import (
    check_palm_image_quality,
    detect_hand_side,
    extract_palm_roi,
    preprocess_palm_roi,
    create_biometric_template,
    compare_biometric_templates,
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
        raise RuntimeError("Missing enrollment: " + user_id)
    if enrollment.get("hand_side") != "right":
        raise RuntimeError("Unexpected hand side: " + user_id)
    enrollments[user_id] = enrollment


def prepare_query(user_id, filename):
    path = DATASET / user_id / filename
    image = cv2.imread(str(path))

    if image is None:
        return None, "Image missing"

    quality = check_palm_image_quality(image)
    if not quality["valid"]:
        return None, "Quality check failed"

    detected = detect_hand_side(image, mirrored=False)
    if (
        detected["hand_side"] != "right"
        or detected["confidence"] < 0.80
    ):
        return None, "Hand side check failed"

    roi = extract_palm_roi(image)
    if roi is None:
        return None, "Palm ROI not detected"

    processed = preprocess_palm_roi(roi)
    template = create_biometric_template(processed)
    return template, None


def compare_all(enrollment, query_template):
    comparisons = [
        compare_biometric_templates(item, query_template)
        for item in enrollment["templates"]
    ]

    return {
        "edge": round(
            mean(item["edge_score"] for item in comparisons), 4
        ),
        "lbp": round(
            mean(item["texture_score"] for item in comparisons), 4
        ),
        "combined": round(
            mean(item["combined_score"] for item in comparisons), 4
        ),
    }


def evaluate(filename):
    rows = []
    invalid = []
    latencies = []

    for user_id in USER_IDS:
        start = time.perf_counter()
        template, error = prepare_query(user_id, filename)

        if template is None:
            invalid.append((user_id, error))
            continue

        genuine_scores = compare_all(
            enrollments[user_id], template
        )

        latencies.append(
            (time.perf_counter() - start) * 1000
        )

        rows.append({
            "genuine": True,
            **genuine_scores
        })

        for claimed_id in USER_IDS:
            if claimed_id == user_id:
                continue

            impostor_scores = compare_all(
                enrollments[claimed_id], template
            )

            rows.append({
                "genuine": False,
                **impostor_scores
            })

    return rows, invalid, latencies


def calculate_metrics(rows, method, threshold):
    tp = tn = fp = fn = 0

    for row in rows:
        accepted = row[method] >= threshold

        if row["genuine"] and accepted:
            tp += 1
        elif row["genuine"]:
            fn += 1
        elif accepted:
            fp += 1
        else:
            tn += 1

    genuine = tp + fn
    impostor = tn + fp

    return {
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "FAR": 100 * fp / impostor if impostor else None,
        "FRR": 100 * fn / genuine if genuine else None,
        "accuracy": (
            100 * (tp + tn) / len(rows) if rows else None
        ),
        "balanced_accuracy": (
            50 * (tp / genuine + tn / impostor)
            if genuine and impostor else None
        ),
    }


def calibrate(rows, method):
    candidates = sorted(
        {0.0, 1.0001} |
        {row[method] for row in rows}
    )

    def rank(threshold):
        result = calculate_metrics(rows, method, threshold)
        return (
            result["balanced_accuracy"],
            -result["FP"],
            threshold
        )

    return max(candidates, key=rank)


def show_results(name, rows, invalid, latencies, thresholds):
    print()
    print("=" * 56)
    print(name)
    print("=" * 56)

    print("Valid comparisons:", len(rows))
    print("Genuine:", sum(r["genuine"] for r in rows))
    print("Impostor:", sum(not r["genuine"] for r in rows))
    print("Invalid images:", invalid)

    if latencies:
        print(
            "Mean genuine end-to-end latency:",
            round(mean(latencies), 2),
            "ms"
        )

    for method in ("edge", "lbp", "combined"):
        threshold = thresholds[method]
        result = calculate_metrics(rows, method, threshold)

        print()
        print("METHOD:", method.upper())
        print("Threshold:", round(threshold, 4))
        print("TP:", result["TP"], "FN:", result["FN"])
        print("FP:", result["FP"], "TN:", result["TN"])
        print("FAR:", round(result["FAR"], 2), "%")
        print("FRR:", round(result["FRR"], 2), "%")
        print("Accuracy:", round(result["accuracy"], 2), "%")
        print(
            "Balanced accuracy:",
            round(result["balanced_accuracy"], 2),
            "%"
        )


print("PALMA - FEATURE COMPARISON EVALUATION")
print("Database: read-only evaluation")
print("Validation: 4.jpg")
print("Final test: 5.jpg")

validation, validation_invalid, validation_times = evaluate("4.jpg")

thresholds = {
    "edge": calibrate(validation, "edge"),
    "lbp": calibrate(validation, "lbp"),
    "combined": 0.90
}

show_results(
    "VALIDATION RESULTS",
    validation,
    validation_invalid,
    validation_times,
    thresholds
)

final, final_invalid, final_times = evaluate("5.jpg")

show_results(
    "INDEPENDENT FINAL TEST RESULTS",
    final,
    final_invalid,
    final_times,
    thresholds
)

print()
print("NOTE: Combined threshold was fixed at 0.90.")
print("Edge and LBP thresholds use validation data only.")
print("Timing covers valid genuine attempts, not all attempts.")
print("Educational evaluation only.")
