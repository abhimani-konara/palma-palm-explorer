# PALMA - ICA02 Biometric Evaluation Results

## 1. Evaluation Method

The system uses three palm images per participant for enrollment.

- Enrollment images: 1.jpg, 2.jpg, 3.jpg
- Validation image: 4.jpg
- Final test image: 5.jpg
- Experimental decision threshold: 0.90
- Evaluated hand side: Right hand

Nine enrolled participants were included in the evaluation.

## 2. Validation Results

| Metric | Result |
|---|---|
| Genuine attempts | 9 |
| Impostor attempts | 72 |
| False rejections | 1 |
| False acceptances | 0 |
| Invalid images | 0 |
| FAR | 0.00% |
| FRR | 11.11% |

## 3. Final Test Results

| Metric | Result |
|---|---|
| Valid genuine attempts | 8 |
| Valid impostor attempts | 64 |
| Correct genuine acceptances | 7 |
| False rejections | 1 |
| False acceptances | 0 |
| Invalid images | 1 (P-F) |
| FAR | 0.00% |
| FRR | 12.50% |


### 3.1. Decision Accuracy and Confusion Matrices

Accuracy is calculated using valid verification decisions only.

Accuracy = (Correct Genuine Acceptances + Correct Impostor Rejections) / Total Valid Attempts * 100

#### Validation Set

| Actual Attempt | Accepted | Rejected |
|---|---:|---:|
| Genuine | 8 | 1 |
| Impostor | 0 | 72 |

Validation accuracy = (8 + 72) / 81 * 100 = 98.77%

#### Independent Final Test Set

| Actual Attempt | Accepted | Rejected |
|---|---:|---:|
| Genuine | 7 | 1 |
| Impostor | 0 | 64 |

Final test accuracy = (7 + 64) / 72 * 100 = 98.61%

The P-F final test image was invalid and excluded from
the 72 valid comparisons. Invalid images are reported separately.

The high decision accuracy must be interpreted cautiously
because impostor comparisons outnumber genuine comparisons.
These classroom results do not establish production security.

## 4. Evaluation Formulas

FAR = (False Acceptances / Valid Impostor Attempts) * 100

FRR = (False Rejections / Valid Genuine Attempts) * 100

Final FAR = (0 / 64) * 100 = 0.00%

Final FRR = (1 / 8) * 100 = 12.50%


## 4.1 Feature Comparison and Processing Time

Three biometric matching configurations were evaluated:

1. Edge-only: Cosine similarity of 64 edge features.
2. LBP-only: Histogram intersection of 256 texture features.
3. Combined: Equal-weight fusion of Edge and LBP scores.

Edge-only and LBP-only thresholds were selected using
the validation images (4.jpg). The Combined threshold
remained fixed at the previously used value of 0.90.

The held-out final images (5.jpg) were not used
to choose these thresholds.

### Validation Results

| Method | Threshold | FAR | FRR | Accuracy | Balanced Accuracy |
|---|---:|---:|---:|---:|---:|
| Edge-only | 0.8794 | 0.00% | 11.11% | 98.77% | 94.44% |
| LBP-only | 0.9274 | 0.00% | 11.11% | 98.77% | 94.44% |
| Combined | 0.9000 | 0.00% | 11.11% | 98.77% | 94.44% |

Validation comparisons:
9 genuine and 72 impostor attempts, with 0 invalid images.

### Final Test Results

| Method | Threshold | FAR | FRR | Accuracy | Balanced Accuracy |
|---|---:|---:|---:|---:|---:|
| Edge-only | 0.8794 | 0.00% | 12.50% | 98.61% | 93.75% |
| LBP-only | 0.9274 | 0.00% | 12.50% | 98.61% | 93.75% |
| Combined | 0.9000 | 0.00% | 12.50% | 98.61% | 93.75% |

Final valid comparisons:
8 genuine and 64 impostor attempts.

One final test image (P-F) failed quality validation
and was excluded from matching metrics.

All three methods produced the same classification
counts at their respective thresholds:

- True accepts: 7
- False rejects: 1
- False accepts: 0
- True rejects: 64

These results do not demonstrate that feature fusion
outperforms either individual method on this dataset.

### Processing Time

| Evaluation | Mean Valid Genuine Attempt Time |
|---|---:|
| Validation | 413.12 ms |
| Final test | 363.41 ms |

The timing measures image quality checks, hand-side
detection, palm ROI extraction, preprocessing,
feature extraction and genuine template comparison.

Image file reading, HTTP handling and authentication
database logging are not included. Timing excludes
invalid attempts and the additional impostor comparisons.

### Experimental Limitations

- Only nine participants were evaluated.
- The recommended classroom dataset size is larger.
- Comparisons share participants and are not independent.
- A zero observed FAR does not guarantee future safety.
- The final images are held out from threshold selection,
  but come from the same participants.
- Liveness detection was not evaluated.
- The prototype is not suitable for production access control.

## 5. Important Observations

- P-A was falsely rejected in the final test.
- P-A genuine similarity score: 0.7880.
- P-F test image was classified as invalid and excluded
  from the valid-comparison FAR and FRR denominators.
- No false acceptances were observed in 64 impostor comparisons.
- Invalid-image handling should be reported separately.
- The threshold is experimental and was evaluated
  on a small dataset.

## 6. Limitations

These results are based on a small number of participants
and correlated comparisons within the same dataset.
A measured FAR of 0% does not prove zero security risk.

This system is an academic prototype and is not validated
for production identity verification.

## 7. Conclusion

PALMA successfully demonstrated biometric enrollment,
encrypted template storage, one-to-one palm verification,
authentication decisions, and authentication logging.

The final evaluation produced a measured FAR of 0.00%
and FRR of 12.50% among valid comparisons.

Further testing and improvement are required before
real-world biometric authentication use.
