# PALMA validation record

## Checks performed

- JavaScript syntax checks: `app.js`, `genesis.js`, `studio.js`, `vision-worker.js`.
- Python compilation: `app.py`, `vision.py`, `llm.py`, `knowledge.py`.
- Flask test client: homepage, status, both-palm multipart analysis, eight image outputs per hand, six-section local report, two chat turns, missing image rejection, corrupt image rejection, dark/blank image rejection, clear session, invalid/cleared scan chat rejection.
- Fixed an inherited OpenCV output-shape issue by normalizing Hough output with `reshape(-1,4)` before iterating.
- Browser: four-line explorer selection, story dialog and scanner navigation; two image uploads; actual JavaScript worker processing; eight processing choices; left/right switch; edge output; measured quality and candidate rows; six report cards; context-aware comparison response.
- Browser report-download action was attempted; the cloud download-event API timed out. Verify the export on the student's own browser before the demonstration. The export implementation uses a JSON Blob and a download link.

## Test fixture

A generated photographic palm was used in both slots for smoke testing. No real participant's biometric data was used. This proves the execution path, not classifier accuracy or a valid left/right comparison study.

## Still required on the student's device

- At least three distinct consented left/right palm pairs, including low-quality/error cases.
- Actual Windows startup and dependency install.
- Real phone and desktop viewport checks.
- Camera allow/deny, switch camera, capture, retake, confirm, and camera indicator off after closing/hiding.
- Download report JSON and processed image.
- Optional MediaPipe installation and verified-landmark cases.
- Live Gemini/OpenAI with the student's own configured account, two follow-up turns, provider failure/fallback case.
- Capture screenshots and record actual outcomes; do not mark these unperformed cases as passed.

## Cinematic update checks

- JavaScript syntax checked for the new `journey.js` and updated `app.js`.
- Browser verified Next room starts the camera-flight state, updates the URL to `#explorer`, and arrives with The living atlas as the active room.
- Browser verified eight destinations in the room selector and developer/footer credit text.
- Full multi-room timed tour, mobile rendering, and performance on the student’s device still require device testing.
