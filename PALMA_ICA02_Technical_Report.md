# PALMA — ICA02 Technical Report
**Palm-Based Biometric Authentication Using Digital Image Processing and Computer Vision**

NIBM Kandy Innovation Centre · Digital Image Processing · In-Class Assessment 02

**Status:** Academic draft for verification · **Version:** 26 November 2026

---

## 1. Abstract

PALMA is a classroom prototype that performs one-to-one palm-image verification. A consenting participant is enrolled using three photographs of the same hand; a later image is subjected to quality checks, landmark-based palm localization, image normalization and numerical feature extraction. The system compares the new features against the three enrolled templates and produces a score and a threshold-based accept/reject decision, or an invalid-image outcome. Its purpose is to demonstrate digital image processing and computer vision—not to provide production-grade identity security.

Nine pseudonymous participants with right-palm samples were evaluated. Images 1–3 were reserved for enrollment, image 4 for validation and image 5 for final testing. On the valid held-out comparisons, the fixed combined-score threshold of 0.90 gave 7 genuine accepts, 1 false reject, 0 false accepts and 64 impostor rejections (FAR 0.00%, FRR 12.50%, accuracy 98.61%). One additional final image failed quality validation. Edge-only and LBP-only methods yielded the same decision counts at their separately selected validation thresholds. These findings are limited to a small, correlated classroom dataset.

## 2. Problem, objectives and scope

Password-based identity checks can be shared or forgotten. Palmprint patterns provide a useful educational case study in image acquisition, hand localization, preprocessing, template design and statistical thresholding. PALMA accepts a claimed participant ID and compares a fresh image with that ID’s stored palm descriptors; it does not search for the identity of an unknown person.

- Develop a repeatable three-image enrollment process for the same palm with unique pseudonymous user IDs and explicit consent.

- Reject unsupported, poor-quality, absent-palm or wrong-hand submissions instead of forcing a biometric score.

- Normalize the palm ROI; implement both principal-crease edge density and local texture descriptors; store protected numerical templates.

- Return an interpretable similarity score and experimental threshold, plus an authentication outcome and audit metadata.

- Evaluate genuine and impostor decisions with a validation/final-test split and disclose errors and ethical constraints.

> **Verification note:** Scope: Educational proof of concept. No liveness or presentation-attack detection has been demonstrated. Do not use for door access, financial services or other consequential decisions.

## 3. System architecture and workflow

The implementation uses a Flask backend (app.py), OpenCV and NumPy for image processing, MediaPipe hand landmarks for ROI localization, SQLite for local template/audit records and Fernet for template encryption. Its interface is provided by the dist/ web assets. Relevant modules include biometric.py, biometric_storage.py, biometric_api.py, biometric_enrollment_api.py and admin_auth.py.

| Stage | Enrollment pathway | Verification pathway |
| --- | --- | --- |
| Input | Participant ID, declared hand, consent, 3 images | Claimed ID, declared hand, fresh image |
| Validation | Format/quality and same-hand checks | Quality, hand-side and enrollment checks |
| Vision | Hand landmarks → palm ROI → 256 × 256 normalization | Same landmark/ROI/preprocessing definitions |
| Features | 64 edge-density values + 256 LBP histogram bins per sample | Matching 64 + 256 features |
| Storage / decision | Encrypt enrolled templates; associate with user ID | Compare against three stored templates; average; threshold |
| Audit / interface | Confirm enrollment status | Show result/score; record attempt metadata |

Verification decisions have three practical categories: Authentication Successful when similarity meets or exceeds the threshold; Authentication Failed when the image is valid but similarity is below the threshold; and Invalid Image when the quality, hand or palm-region checks fail. The administrative flow is intended for controlled local testing.

## 4. Dataset and experimental protocol

The local experiment included nine pseudonymous IDs: P-A, P-B, P-F, P-G, P-H, P-I, P-J, P-K and P-P. For each, the right palm was designated as the expected hand. Files 1.jpg, 2.jpg and 3.jpg form each enrollment; 4.jpg serves as a separate validation image; and 5.jpg is reserved for final testing. A genuine attempt claims its own ID. Impostor attempts reuse a valid query image while claiming each of the other eight IDs.

| Split | Valid genuine | Valid impostor | Invalid images |
| --- | --- | --- | --- |
| Validation: 4.jpg | 9 | 72 | 0 |
| Final: 5.jpg | 8 | 64 | 1 (P-F) |

The final invalid P-F image is reported separately, not counted as a correct rejection or added to the FAR/FRR denominators. Final threshold selection is not performed on 5.jpg. Dataset files and biometric templates are local; none should be published in the source repository.

> **Verification note:** Consent verification: the participant recruitment record, written/recorded consent, collection conditions and withdrawal arrangements were not independently inspected for this report. Attach or verify these records before final submission. The brief recommends at least 10 participants; this experiment used 9.

## 5. Palm localization and preprocessing

### 5.1 Landmark-based region of interest

extract_palm_roi() converts the input from BGR to RGB, then runs MediaPipe Hands in static-image mode (one hand, minimum detection confidence 0.5). It retrieves landmark 0 (wrist), 5 (index-finger base) and 17 (little-finger base). These points define a palm-width direction and approximate upper/lower ROI corners. cv2.getPerspectiveTransform() computes a mapping from the four estimated corners to a square, and cv2.warpPerspective() produces a 256 × 256 ROI. If landmarks are missing, the function returns no ROI.

### 5.2 Processing steps and parameters

| Technique | Implementation / purpose |
| --- | --- |
| Resizing and alignment | Perspective-warped palm ROI with 256 × 256 target dimensions |
| Grayscale | cv2.cvtColor(..., cv2.COLOR_BGR2GRAY), when input is color |
| Noise reduction | GaussianBlur kernel (3,3), sigma chosen automatically (0) |
| Contrast enhancement | CLAHE with clipLimit 2.0 and tileGridSize (8,8) |
| Quality handling | check_palm_image_quality() rejects unsuitable samples; hand-side detection below 0.80 confidence is rejected in verify_palm_image() |

The same preprocessing definition is applied to enrollment and query samples. Perspective normalization helps reduce hand orientation differences but does not guarantee accurate alignment for every pose, background or illumination condition. Image-stage screenshots (original, ROI, grayscale, enhanced and edge view) should be captured for demonstration; their availability in the current interface requires a final visual check.

## 6. Feature extraction and template construction

### 6.1 Method A: Canny edge density

extract_edge_features() applies cv2.Canny with thresholds 60 and 140 to the preprocessed grayscale ROI. The resulting edge image is partitioned into 8 × 8 spatial blocks. In each block, nonzero edge pixels are divided by the block’s area, generating a 64-dimensional vector. This method describes the spatial distribution of prominent line-like structures but is sensitive to contrast, blur and misaligned regions.

### 6.2 Method B: Local Binary Patterns (LBP)

extract_lbp_features() compares each interior pixel to its eight neighbors, setting a bit when the neighbor intensity is greater than or equal to the center intensity. The 8-bit code ranges from 0 to 255. Counting codes creates a 256-bin histogram, subsequently divided by its total count. The method represents local texture but loses explicit global spatial arrangement and can change under illumination or noise.

### 6.3 Template structure

create_biometric_template() returns a versioned numerical object containing a 64-value edge_features list and a 256-value lbp_features list. Enrollment retains three such templates per participant, rather than storing raw photos as authentication templates. Template format validation checks version, vector lengths, finite values and non-negativity during comparison.

## 7. Matching method and thresholding

The matcher calculates cosine similarity between the 64-element edge vectors. For LBP, histograms are normalized and compared using histogram intersection: the sum of the elementwise minimum across all 256 bins. Both values are clipped to [0,1], and a fused score is computed as 0.5 × edge score + 0.5 × LBP score. For each query, the score is computed against all three enrolled templates and averaged; verification accepts when the averaged similarity is greater than or equal to its selected threshold.

The fixed combined-method threshold in the recorded experiment was 0.9000. The separate edge-only threshold (0.8794) and LBP-only threshold (0.9274) were selected using 4.jpg validation results to maximize balanced accuracy, with ties favoring fewer false accepts and then the higher threshold. These thresholds were then applied unchanged to 5.jpg. The combined threshold should be described as experimental; its earlier selection was not independently verified from the supplied logs. Similarity is not a calibrated probability of identity.

## 8. Results and interpretation

### 8.1 Method comparison

| Set / method | Threshold | FAR | FRR | Accuracy | Balanced acc. |
| --- | --- | --- | --- | --- | --- |
| Validation / Edge | 0.8794 | 0.00% | 11.11% | 98.77% | 94.44% |
| Validation / LBP | 0.9274 | 0.00% | 11.11% | 98.77% | 94.44% |
| Validation / Combined | 0.9000 | 0.00% | 11.11% | 98.77% | 94.44% |
| Final / Edge | 0.8794 | 0.00% | 12.50% | 98.61% | 93.75% |
| Final / LBP | 0.9274 | 0.00% | 12.50% | 98.61% | 93.75% |
| Final / Combined | 0.9000 | 0.00% | 12.50% | 98.61% | 93.75% |

### 8.2 Confusion matrices (combined method)

| Split | True accept (TP) | False reject (FN) | False accept (FP) | True reject (TN) |
| --- | --- | --- | --- | --- |
| Validation | 8 | 1 | 0 | 72 |
| Final | 7 | 1 | 0 | 64 |

FAR = FP / (FP + TN); FRR = FN / (FN + TP); accuracy = (TP + TN) / all valid comparisons. Balanced accuracy = 0.5 × [TP/(TP+FN) + TN/(TN+FP)]. In the final set, accuracy is (7+64)/72 = 98.61%; FRR = 1/8 = 12.50%; FAR = 0/64 = 0.00%. One P-F final image was invalid and is excluded from valid-comparison metrics.

The three methods generated identical accept/reject counts at the evaluated thresholds, so the experiment does not demonstrate that feature fusion outperforms either individual technique. The imbalance (64 impostor versus 8 genuine comparisons) inflates the intuitive impression given by overall accuracy; balanced accuracy and separate FAR/FRR are therefore essential.

### 8.3 Timing and observed errors

| Split | Mean latency for valid genuine attempts |
| --- | --- |
| Validation | 413.12 ms |
| Final | 363.41 ms |

These timings cover quality/hand checks, ROI extraction, preprocessing, feature extraction and genuine-template matching as measured in the feature-ablation script. They do not include disk image loading, HTTP handling, audit database writes, invalid attempts or the extra impostor comparisons. The P-A genuine sample was falsely rejected in final testing (recorded combined similarity 0.7880). P-F failed the final image quality check. Both failures should be demonstrated and discussed rather than hidden.

## 9. Security, privacy and ethical safeguards

Numerical enrollment templates are encrypted using the cryptography Fernet library before being placed in a local SQLite database. The encryption key is obtained from an environment variable (PALMA_BIOMETRIC_KEY); administrator access uses a password-hash setting rather than a plaintext password in source. Local administrative endpoints include session/CSRF-related protections, and authorization/input-validation checks were exercised with automated tests. No secret value, live biometric database or participant image belongs in the repository.

The audit database schema contains an authentication attempt ID, claimed user ID, timestamp, score, outcome and processing duration. It is designed to record metadata rather than raw palm photos. These mechanisms do not constitute a complete security audit; configuration, host binding, browser cookies, rate limiting, storage permissions and key rotation still require a deployment-specific review.

Participants must give informed consent, be able to withdraw and have associated templates deleted; storage-retention duration and operational deletion procedures must be documented and tested before broader use. A photograph, printout or displayed image can spoof a simple image-based matcher: no liveness/presentation-attack capability was demonstrated. Biometric information is sensitive and cannot be treated like a resettable password.

**Implementation update (28 November 2026):** An admin-authenticated, localhost-restricted, CSRF-protected deletion API now removes a participant enrollment and matching authentication history after ID confirmation. Seven automated API tests passed using temporary databases. The deletion interface was visually verified after admin login and confirmed hidden after logout. A full browser-to-database deletion demonstration and participant consent records still require verification.

## 10. Software testing and reproducibility

The project’s automated suite last reported 34 of 34 tests passing: 8 ICA01 tests, 19 existing ICA02 tests, and 7 secure participant-deletion API tests. Tests used a temporary SQLite database and generated test keys where applicable; a test pass does not establish overall security, image-quality generalization or production readiness.

Research scripts include final_test_5.py (held-out combined-score evaluation), validation_4.py (validation comparisons), calibrate_biometrics.py (score analysis) and feature_ablation_eval.py (method-specific validation and final-test metrics). To reproduce the reported findings, the original consented dataset, encrypted enrollment templates, correct local decryption key and compatible installed dependencies must be available. Keep these sensitive prerequisites outside public Git.

### ICA02 UI implementation update (28 November 2026)

The submitted review patch adds a localhost-only, admin-session-protected
`GET /api/biometric/history` endpoint returning the newest 50 metadata-only
authentication attempts, with an optional validated participant ID filter.
The UI now renders this audit table without injecting participant strings
as HTML. The verification API optionally returns temporary PNG previews of
observed MediaPipe landmarks, the extracted palm ROI, grayscale, Gaussian
filtering, CLAHE, Canny edges and LBP codes; the interface clears these
previews on logout. The backend does not save preview images.

A fresh install now requires a compatible pinned MediaPipe release and
cryptography. The admin setup helper creates the biometric key only when
that will not risk overwriting encrypted existing enrollments. This patch
includes dedicated automated API tests, but installation, a real browser
flow and evidence must still be verified by the student before claiming
submission readiness. Prior experimental rates are intentionally unchanged.

## 11. Limitations and planned improvements

- Nine participants fall below the brief’s recommended 10; correlated impostor attempts and one invalid image limit statistical confidence. A measured FAR of 0.00% does not mean the false-accept risk is zero.

- The ROI depends on MediaPipe landmark detection and uses only a small set of reference points; severe pose, occlusion, glare and background changes may destabilize alignment.

- LBP discards much spatial information, while Canny-derived edge density can confuse palm creases with noise or incidental contours. Fusion did not improve decisions in the measured experiment.

- Method-specific thresholds were tuned on a very small validation set; report selection bias and avoid claiming calibrated identity probabilities.

- Presentation-attack detection, a fully verified browser-to-database withdrawal/deletion workflow, full participant consent records, gallery/history browser verification on a real enrolled test image and broader cross-device evaluation remain to be confirmed or completed.

- Future experiments should acquire more consenting participants, test acquisition variability, compare threshold sensitivity/ROC curves, preserve strict train-validation-test separation, and report latency for both successful and invalid submissions.

## 12. Demonstration and submission checklist

- Present a three-image enrollment with consent and a pseudonymous ID; show the stored template is numerical and encrypted without revealing its value.

- Show original palm, detected landmarks, aligned ROI, enhanced grayscale and Canny edge results; verify actual UI availability before claiming these screenshots as evidence.

- Demonstrate a genuine accept, a genuine false reject or impostor reject, and an invalid image, displaying similarity, threshold and status.

- Show a sanitized authentication history (attempt ID, ID, time, score, outcome, duration); redact any participant-related details.

- Explain the validation/final split, 64-edge/256-LBP descriptors, fixed combined threshold, confusion matrices and limitations in a 5–10 minute video and live viva.

- Verify that requirements.txt, sample .env.example, setup/run instructions, schema, dataset/consent notes, evidence screenshots and references are included in the submission pack.

## 13. Conclusion

PALMA demonstrates a reproducible classroom pipeline from palm-image acquisition through MediaPipe-assisted ROI localization, OpenCV preprocessing, edge/LBP feature extraction, encrypted enrollment and one-to-one similarity decisions. On 72 valid final comparisons, it observed an accuracy of 98.61%, FAR of 0.00% and FRR of 12.50%, with one additional invalid image. These are limited experimental measurements, not a warranty of biometric security. More participants, improved acquisition robustness, full end-to-end deletion verification and additional adversarial tests are needed before considering broader operation.

## References and evidence basis

[1] NIBM Kandy Innovation Centre. In-Class Assessment 02: Palm-Based Biometric Authentication System. Assessment brief supplied for the Digital Image Processing module.

[2] PALMA project source: biometric.py; biometric_storage.py; biometric_api.py; biometric_enrollment_api.py; admin_auth.py; feature_ablation_eval.py; final_test_5.py; validation_4.py; ICA02_EVALUATION_RESULTS.md. Development branch: https://github.com/abhimani-konara/palma-palm-explorer/tree/ica02-biometric-development

[3] OpenCV Documentation. Image processing, Canny edge detection, Gaussian filtering, CLAHE and perspective transforms. https://docs.opencv.org/4.x/

[4] Google AI for Developers. MediaPipe hand landmark detection. https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker

[5] cryptography documentation. Fernet authenticated symmetric encryption. https://cryptography.io/en/latest/fernet/

[6] Python documentation. sqlite3 database interface. https://docs.python.org/3/library/sqlite3.html

> **Verification note:** Preparation note: This is a source-grounded academic draft based on the code snippets, test logs, README and evaluation outputs supplied in the PALMA project discussion. Verify interface screenshots, consent records, participant provenance, full source/configuration and citation formatting before final submission.
