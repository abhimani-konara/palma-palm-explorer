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

## 4. Evaluation Formulas

FAR = (False Acceptances / Valid Impostor Attempts) * 100

FRR = (False Rejections / Valid Genuine Attempts) * 100

Final FAR = (0 / 64) * 100 = 0.00%

Final FRR = (1 / 8) * 100 = 12.50%

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
