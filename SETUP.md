# Setup Guide

End-to-end setup for the GL-style OMR system: classical OpenCV pipeline with a Claude vision fallback for ambiguous marks.

## Prerequisites

- **Python 3.10+** (the OMR engine uses modern type-hint syntax)
- **Node 18+** (the operator UI is React + Vite)
- **An Anthropic API key** for the Claude vision fallback — get one at <https://console.anthropic.com/>
- **A document scanner** — any flatbed or sheetfed scanner that produces PNG, JPG, or TIFF

## 1. Install Python dependencies

From the project root:

```bash
pip install -r omr_engine/requirements.txt
```

Pulls OpenCV, FastAPI, ReportLab, openpyxl, the Anthropic SDK, and Pydantic.

## 2. Install Node dependencies

```bash
npm install
```

## 3. Configure environment variables

Copy `.env.example` to `.env` and fill in:

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required for the Claude vision fallback. Without it, ambiguous marks stay marked as ambiguous and require manual review |
| `OMR_ENGINE_URL` | Base URL of the Python engine. Leave at `http://localhost:8000` for local dev |
| `OMR_MARKED_THRESHOLD` | CV "marked" threshold. Higher = stricter. Default `0.18` |
| `OMR_BLANK_THRESHOLD` | CV "blank" threshold. Higher = more boxes go to ambiguous review. Default `0.04` |

## 4. Build the printable answer-sheet templates

```bash
python -m omr_engine.pdf.generate
```

Produces 4 paired PDFs and JSON sidecars in `omr_engine/templates/`:

- `AE_STANDARD` — 50-question A-E standard layout
- `ADN_STANDARD` — 50-question A / D / N variant
- `MULTI_SECTION` — Verbal A-E + Numerical A-D + True/False on one sheet
- `AE_TWOMARK` — A-E with two-mark questions in Q21-30

The PDF and the JSON sidecar are produced by the same code path so the printed page geometry can never drift from the engine's expectations.

## 5. Start the OMR engine

In one terminal:

```bash
uvicorn omr_engine.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify at <http://localhost:8000/health> — should return `{"status": "ok"}`.

## 6. Start the operator UI

In another terminal:

```bash
npm run dev
```

Open <http://localhost:3000>.

## First-run workflow

1. **Print** any of the PDFs from `omr_engine/templates/` on plain A4 paper
2. **Hand to students** — they mark answers with a thin horizontal line in the chosen rectangular box (NOT shading), and fill in their student ID by lining boxes in the bubble grid at the top of the sheet
3. **Scan** the completed sheets on any document scanner — output to PNG, JPG, or TIFF
4. **Open the UI** → click **New Scan** → select all the scanned files
5. The pipeline auto-detects the template, aligns each page via the corner fiducials, classifies every box, and escalates ambiguous marks to Claude in a single batched call
6. Review any AI-flagged marks in the **Review Queue** tab — the cropped image appears alongside the AI's verdict, and operator overrides re-score the sheet immediately
7. Export results from the **Data Export** tab as CSV or XLSX

## Verifying the install with synthetic samples

```bash
python -m samples.generate       # synthesize filled test scans + ground truth
python -m scripts.test_harness   # run the engine and report accuracy
```

Expected: 99%+ accuracy on the clean synthetic samples. The harness exercises the full pipeline (deskew → fiducials → align → classify) end-to-end, so a regression in any stage shows up as a drop in the reported number.

## Building the deliverables package

```bash
python -m scripts.build_deliverables
```

Copies the printable PDFs and the synthetic samples into a `deliverables/` directory ready to hand off.

## Troubleshooting

- **"OMR engine unreachable"** — make sure `uvicorn` is running on port 8000 and `OMR_ENGINE_URL` matches
- **"Found only N fiducial candidates, need 4"** — the scan is cropped or the fiducials are missing/damaged. Re-print the template and re-scan with the page fully on the platen
- **All marks classified ambiguous** — the scanner is producing unusually high or low contrast. Lower `OMR_MARKED_THRESHOLD` and raise `OMR_BLANK_THRESHOLD` in `.env`, then restart the engine
- **Claude classifications failing** — verify `ANTHROPIC_API_KEY` is set and your account has credit. The pipeline still works without it; you just lose the AI escalation for ambiguous marks
- **Student ID showing `?` characters** — at least one digit position has no mark or has competing marks. Check the warning list in the sheet's `process_result.warnings`
