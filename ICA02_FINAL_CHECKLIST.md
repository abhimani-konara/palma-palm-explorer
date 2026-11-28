# PALMA ICA02 - final handover and verification

Updated 28 November 2026. **This is a checklist, not a claim that every live
integration check was performed.**

## Implemented in code

- [x] Consent-gated, 3-image enrollment with palm quality/hand-side checks
- [x] MediaPipe ROI extraction, 256 x 256 normalization, Gaussian + CLAHE
- [x] Two compared features: 64 edge-density values and 256 LBP bins
- [x] Encrypted numerical templates, 1-to-1 matching at 0.90 threshold
- [x] Genuine/impostor evaluation with held-out test samples (9 subjects)
- [x] Admin local auth, CSRF, enrolment, deletion, auditable verification
- [x] Code for in-memory gallery and read-only authentication log UI
- [x] New-group setup and dependencies documented

## Important checks before submission

- [ ] Run all tests locally and record fresh pass count
- [ ] Run full site from a clean ZIP on another computer if feasible
- [ ] Confirm actual authorized browser enrollment and verification
- [ ] Confirm eight processing previews appear for a valid test sample
- [ ] Confirm history table shows attempt ID, user ID, UTC time, score,
      outcome and processing duration; refresh after failed/invalid test
- [ ] Test deletion using a **new disposable, consenting test ID** only;
      confirm both template and history rows removed
- [ ] Attach consent evidence for the **nine** evaluated participants,
      with separately stored permission records and a withdrawal procedure
- [ ] Verify screenshots of ROI, enhanced grayscale and Canny output
- [ ] Prepare 5-10 minute demonstration video showing genuine success,
      impostor rejection, invalid-image behavior, gallery and history
- [ ] Submit report, source ZIP, setup notes and references as lecturer asks

## Scope and evaluation integrity

The NIBM ICA02 brief recommends 10 consenting participants with five images
per participant. The completed reported evaluation uses **9**. P-D 3.jpg
was rejected for blur; P-E 1.jpg failed blur and hand confidence. Do **not**
reuse held-out test images for enrollment to artificially raise the count,
and do not report unverified new performance metrics. Existing recorded
final-test observations are 7 genuine accepts, 1 false reject, 64 impostor
rejects, 0 false accepts and 1 invalid image. FAR 0% is a measured small-
sample rate, not a guarantee of zero real-world false accepts.

Keep all real biometric images, encryption keys, database files and live API
keys out of the group source ZIP and public repository. Each member can
configure their own local `.env`. Keep consent records privately.
