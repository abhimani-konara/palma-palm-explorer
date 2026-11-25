
from itertools import combinations
from statistics import mean

from biometric_storage import load_enrollment
from biometric import compare_biometric_templates


PARTICIPANT_IDS = [
    "P-A", "P-B", "P-F",
    "P-G", "P-H", "P-I",
    "P-J", "P-K", "P-P"
]

enrollments = {}

print("PALMA - Biometric Score Analysis")
print("-" * 45)

# Load enrolled participants
for user_id in PARTICIPANT_IDS:
    enrollment = load_enrollment(user_id)

    if enrollment is None:
        raise ValueError(f"Enrollment missing: {user_id}")

    if len(enrollment["templates"]) != 3:
        raise ValueError(f"Invalid template count: {user_id}")

    enrollments[user_id] = enrollment

genuine_scores = []
impostor_scores = []

# Compare templates belonging to the same person
for user_id in PARTICIPANT_IDS:
    templates = enrollments[user_id]["templates"]

    for template_a, template_b in combinations(templates, 2):
        result = compare_biometric_templates(
            template_a,
            template_b
        )
        genuine_scores.append(result["combined_score"])

# Compare templates belonging to different people
for user_a, user_b in combinations(PARTICIPANT_IDS, 2):
    templates_a = enrollments[user_a]["templates"]
    templates_b = enrollments[user_b]["templates"]

    for template_a in templates_a:
        for template_b in templates_b:
            result = compare_biometric_templates(
                template_a,
                template_b
            )
            impostor_scores.append(result["combined_score"])


def show_statistics(name, scores):
    print(f"\n{name}")
    print("Comparisons:", len(scores))
    print("Minimum:", round(min(scores), 4))
    print("Average:", round(mean(scores), 4))
    print("Maximum:", round(max(scores), 4))


show_statistics("GENUINE SCORES", genuine_scores)
show_statistics("IMPOSTOR SCORES", impostor_scores)

print("\nScore ranges overlap:",
      max(impostor_scores) >= min(genuine_scores))

print("-" * 45)
print("Development score analysis completed")
