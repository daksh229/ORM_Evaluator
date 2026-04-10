# Demo Video Script

A 2-minute screen recording showing the end-to-end workflow. Record the screen plus a voiceover.

## Pre-recording setup

- One printed `AE_STANDARD.pdf`, filled in by hand with thin horizontal lines
- A second printed sheet with at least 2-3 deliberately faint or partly-erased marks (to trigger the review queue)
- Both sheets pre-scanned to PNG / JPG
- The Python engine running: `uvicorn omr_engine.main:app --port 8000`
- The Node UI running: `npm run dev`
- The dashboard cleared of prior sessions
- Two browser tabs: <http://localhost:3000> and a file explorer showing `omr_engine/templates/`

## Storyboard

### 0:00 – 0:15 — Hook
- Hold the printed answer sheet to camera
- **VO:** "GL-style 11+ answer sheets use thin horizontal lines instead of bubbles. Generic OMR tools don't handle them. Here's how this system does, end-to-end."

### 0:15 – 0:30 — Templates
- Switch to the file explorer → open `AE_STANDARD.pdf`
- Show the printed corner fiducials and the QR code
- **VO:** "Four template variants ship out of the box: standard A-E, A-D-N, multi-section, and a two-mark variant. Every template has corner fiducials for perspective alignment and a QR code for auto-detection."

### 0:30 – 0:50 — Upload
- Switch to the UI dashboard
- Click **New Scan** → file picker → select both pre-scanned sheets
- Watch the upload progress bar advance from 0/2 to 2/2
- **VO:** "Drop your scans into the UI. The Python OpenCV engine deskews each page, locates the four corner fiducials, perspective-corrects to a canonical millimetre grid, and runs horizontal-line detection on every box."

### 0:50 – 1:10 — Dashboard
- Land on the new session row in the dashboard table
- Hover the row to show the row-hover state
- **VO:** "Each batch becomes a session. The classical CV pre-filter handles about 95% of marks deterministically — fast, offline, and free."

### 1:10 – 1:35 — Review Queue
- Click into the **Review Queue** tab from the sidebar (note the red badge with the count)
- Show 2-3 cards with real cropped box images, each with the AI's verdict and reason
- **VO:** "The remaining 5% — light marks, erasures, smudges — get escalated to Claude vision in a single batched call. The operator sees the actual cropped image, the AI's confidence, and can override with one click."
- Click **Marked** on one card → card disappears, badge count decreases
- **VO:** "Overrides re-score the sheet immediately, so exports always reflect the operator's final word."

### 1:35 – 1:55 — Export
- Switch to the **Data Export** tab
- The session is pre-selected from the dashboard click
- Show the populated table: student IDs read from the bubble grid, scores, wrong-question lists, ambiguous counts
- Click **Export CSV** → file downloads
- Open the CSV in a spreadsheet app to show real columns
- **VO:** "Real CSV and XLSX exports — student ID, score, wrong-question list, and ambiguous flags — straight into your school management system."

### 1:55 – 2:00 — Outro
- Cut to a terminal showing `python -m scripts.test_harness` output with the accuracy summary
- **VO:** "Hybrid OCR plus Claude vision. Robust enough for real exam mocks, transparent enough that every uncertain mark is logged for review."

## Recording tips

- Run the engine and the UI before you start — the demo should never show a loading spinner
- Pre-fill the test sheets cleanly so the dashboard / export tab look populated
- Use a screen recorder that captures keystrokes (e.g. ScreenFlow, OBS, Loom)
- Keep the cursor moving deliberately — no idle pauses
- Aim for under 2:00; trim aggressively
