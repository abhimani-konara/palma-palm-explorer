# PALMA — Ancient art, modern palm exploration

Designed & developed by **Abhimani Konara**. © 2026 Abhimani Konara. All rights reserved. Credits for supplied/generated visuals remain listed below.

A complete academic palm-image exploration application, built from the supplied group-project Python modules and the PALMA interface. The look combines a user-controlled fresco-to-cyber transition, jewel colors, a photographic palm, line hotspots, layered depth, a rotating/zoomable artwork, a heritage room, and decorative flying doves.

## Open the website

- **Hosted PALMA website:** [Open PALMA online](https://palma-sanctuary-abhi.dewmikonara22.chatgpt.site). This is a private site; sign in with the owner's authorized ChatGPT account.
- **Local PALMA on your laptop:** [http://127.0.0.1:5001](http://127.0.0.1:5001), after starting the server with the Windows instructions below. Keep the server terminal open.
- **GitHub repository:** [Source code](https://github.com/abhimani-konara/palma-palm-explorer). This link displays the code; it does not run the Flask application.

A `127.0.0.1` address always refers to the device opening the link. It is not a public website address and cannot be used by someone else to access your laptop's server.

## Start on Windows

1. Extract the ZIP fully. Do not run it from inside the ZIP preview.
2. Install Python 3.11 or 3.12 and enable **Add Python to PATH**.
3. Open the actual project folder containing `app.py`, `dist/`, and `run_windows.bat`. The extracted download may have an outer folder and an inner `PALMA_Full_Project` folder.
4. Click File Explorer's address bar, type `cmd`, and press Enter.
5. Run these commands one at a time:

```bat
set PORT=5001
run_windows.bat
```

6. Wait for `Running on http://127.0.0.1:5001`, then open [http://127.0.0.1:5001](http://127.0.0.1:5001) in Chrome.
7. Keep that terminal open while using the app. Press Ctrl+C to stop.

These instructions select port **5001** so PALMA can run separately from LineLens on port 5000. The application's unchanged default is 5000 if no `PORT` is set. Open the exact address printed by the terminal.

The first setup installs packages and needs an internet connection. There is no API key required for the default local knowledge mode.

## Start on macOS / Linux

```sh
chmod +x run_mac_linux.sh
./run_mac_linux.sh
```

Or manually:

```sh
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
pip install -r requirements.txt
# Copy .env.example to .env, then:
python app.py
```

## What works

- Cinematic room travel: perspective departure/arrival, glowing archway passage, eight-room selector, Next room, and an opt-in automatic tour.
- Gold rain across the whole site and a user-triggered gold-dust shower.
- Genesis dial: drag/swipe, mouse wheel, arrow keys, Home/End, play/pause/reset.
- Photographic line explorer: four clickable illustrated line locations, story dialogs, tilt, zoom, spin and reset; switch to the supplied heritage artwork.
- Separate left/right JPG/PNG inputs and drag/drop; readable file, dimension and quality errors.
- Explicit camera permission, live preview, manual still capture, review, retake, confirm, and front/back camera selection where available. Camera tracks stop on close or tab hiding.
- Eight real image views per hand: normalized original, grayscale, Gaussian, local contrast enhancement, edges, Otsu threshold, morphology, and actual candidate annotations.
- Brightness, contrast, sharpness, candidate counts, uncertainty and warnings.
- Six cultural report topics, visual left/right comparison, report JSON export, processed image export.
- Session-aware local knowledge guide; optional configured Gemini/OpenAI report and contextual conversation.
- Clear session and chat; responsive layouts, keyboard controls and reduced-motion support.

## Two execution modes

| | Hosted website | Local Python application |
|---|---|---|
| Image processing | Browser JavaScript + dedicated worker | Flask + OpenCV + NumPy |
| Contrast | Tiled clipped histogram equalization with interpolation | OpenCV CLAHE |
| Edges | Sobel magnitude + adaptive threshold | OpenCV Canny |
| Line candidates | Supported segment search in an unverified central region | Hough line segments and geometric association |
| Hand localization | Not verified | Optional MediaPipe; unverified fallback if unavailable |
| Chat/report | Curated local knowledge | Curated knowledge or configured live provider |
| Photos | Stay in browser page memory | Sent to local Flask server; not permanently stored |

`dist/` can also be served as an independent static website. It automatically detects a compatible `/api/status`; when running under the included Flask app, it uses the Python API for analysis.

## Optional live AI

Edit only the local `.env` file. Never put keys in HTML/JS or share a real `.env`.

```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=YOUR_KEY
GEMINI_MODEL=gemini-2.5-flash
```

Alternatively:

```ini
LLM_PROVIDER=openai
OPENAI_API_KEY=YOUR_KEY
OPENAI_MODEL=gpt-4o-mini
```

Restart the Python app. Use a provider/model your account can access. API availability, billing and quota depend on your provider. A provider failure falls back with an explicit demo/fallback mode. There is no API key included.

The model receives structured image features, curated knowledge notes and recent conversation messages, **not raw palm photos**. This is retrieval-grounded prompting; it is not a fine-tuned palmistry model.

## Optional hand landmarks

```sh
pip install -r requirements-optional.txt
```

The supplied Python module attempts MediaPipe's `solutions.hands`. Availability depends on the installed MediaPipe API and Python/platform combination. If unavailable, analysis continues with an honestly labeled unverified central region. Landmarks do not verify the names of palmistry creases. No automatic camera hand tracker is shipped in this revision; capture is manual after visual framing.

## Source layout

```text
app.py                  Flask routes and temporary session cache
vision.py               OpenCV stages, quality, optional landmarks, candidates
llm.py                  optional provider calls and local report/chat fallback
knowledge.py            keyword retrieval
knowledge/palmistry.json curated editorial cultural notes
requirements.txt        required Python dependencies
requirements-optional.txt optional MediaPipe dependency
.env.example            safe placeholder settings
run_windows.bat         Windows launcher
run_mac_linux.sh        macOS/Linux launcher
dist/index.html         full interface
dist/style.css          layout, themes and animation
dist/app.js             atlas, navigation, artwork controls, particles
dist/genesis.js         interactive fresco transformation
dist/journey.js         camera-style navigation, tour, gold dust
dist/studio.js          uploads, camera, lab, report and chat
dist/vision-worker.js   browser image-processing fallback
dist/assets/            supplied and generated art, MP4 backdrop
VALIDATION.md           checks performed and remaining device tests
```

## API

- `GET /api/status`: actual provider/engine state.
- `POST /api/analyze`: multipart fields `left` and `right`; returns hands, real images, report and scan ID.
- `POST /api/chat`: JSON `scan_id`, `message`, optional `history`.
- `POST /api/session/clear`: JSON `scan_id`; clears that cached record.

Python keeps at most 18 compact feature/report records in process memory. The cache excludes image outputs; records expire after one hour and are pruned on analysis/chat activity. Restarting the server clears them. Browser results remain in page memory; replacing inputs invalidates old results, and Clear session removes them. Nothing persists across devices.

## Academic limits

This is a **palm-image processing and cultural interpretation project**, not biometric identity authentication. Neither pipeline includes a trained palmistry-line classifier. All line associations are exploratory and low confidence. Background edges can be selected. The decorative atlas lines are illustrative and never substituted for actual observations.

Palmistry is not a scientifically validated way to predict health, lifespan, personality, wealth, relationships, career outcomes or future events. The report must be presented as cultural context, separate from measured image properties.

Use your own consented left/right photographs to evaluate the assignment. The generated sample used for smoke testing is not evidence of real-world recognition accuracy.

## Visual provenance

- Fresco reference: user-supplied Creation of Adam image. Its file includes third-party attribution markings; this project does not establish new rights to the photograph.
- Traditional decorative palm: user-supplied reference; retained as cultural/decorative art, not detection evidence.
- Photographic hand and dove: generated visual assets.
- All interactive motion is layered photographic/CSS/Canvas depth, not an actual volumetric anatomical model or a generated 3D video.

For redistribution beyond a private academic demo, confirm permission for supplied photographs and references. Font loading uses Google Fonts with local serif/sans fallbacks. The image-processing workflow remains functional without the web fonts.

## See the new motion

Press **Take the cinematic tour** on the opening screen, or the play icon in the bottom room navigator. It moves through the eight rooms with a pause at each stop. Stop with the pause icon. **Next room** travels once, the compass opens the room selector, and **✦** releases gold dust. Motion controls and operating-system reduced-motion preferences are respected. The camera path is a layered perspective effect, not a rendered 3D world.

## For Fun — Palmistry Story Reading

After analyzing both palms, select **For Fun Reading** in the Field Notes section. Choose Adventure, Friendship & connection, or Creativity & purpose, optionally select your own symbolic line shapes, and create an imagined three-chapter story. The notice **For fun only — not a factual prediction** stays visible. Stories can be downloaded as JSON.

No database is required. Without an AI key, an explicitly labeled local authored story is shown. The Python app can use the configured Gemini/OpenAI provider; provider failures fall back with a visible label. Only candidate counts, user-selected symbols, theme, and curated notes are sent to that provider—not raw photos. Manual symbols are storytelling prompts, not verified line classifications.

The new endpoint is `POST /api/fun-reading` with `scan_id`, `theme`, and optional `choices`. A current analyzed session is required. Replacing images or clearing the session invalidates its story. This feature is included in the GitHub source for local/Render deployment; the separate ChatGPT-hosted preview is not automatically updated by GitHub pushes.

Feature checks: six Flask/local-story tests cover session expiry and clearing, bad inputs, actual candidate counts, provider response validation/fallback, and exclusion of raw photos from the AI prompt. Run `python -m unittest discover -s tests -v`. The vision module is stubbed in these story tests, so they do not test recognition accuracy. JavaScript syntax was checked; full browser story-flow and live AI-provider testing remain to be done.
