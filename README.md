# MockExam OMR System — Hybrid OCR + Claude Vision

A robust OMR (Optical Mark Recognition) workflow purpose-built for **GL/Kent/Bucks-style 11+ mock exam answer sheets**, where pupils mark answers with a thin horizontal line inside a small rectangular box — *not* by shading bubbles.

## Why This Approach

Generic bubble-sheet tools (FormScanner, OMRChecker, FormRead) fail on horizontal-line answer sheets because they look for filled circles, not directional strokes. Pure-LLM approaches are slow, expensive, and unpredictable at scale.

This project takes a **hybrid two-layer approach** that combines the best of both:

### Layer 1 — Classical Computer Vision (handles ~95% of marks)
- Deskew + perspective correction via fiducial markers
- Adaptive thresholding tolerant of normal print/scan variation
- **Horizontal-line detection** using directional morphological kernels — the key technique that distinguishes a deliberate line from a smudge, dot, or stray pencil mark
- Two-threshold classification: clear marks → `marked`, clearly empty → `blank`, anything in between → escalated

### Layer 2 — Claude Vision (handles the ambiguous ~5%)
- Light marks, partial erasures, smudges, double-marks, and edge cases are escalated to **Claude's vision model** for human-level judgment
- Cheap (`claude-haiku-4-5`) for routine ambiguous cases
- Powerful (`claude-sonnet-4-6`) reserved for the hardest calls
- Every AI-classified mark is logged with a confidence score and surfaced in the **Review Queue** for optional human verification

The result: classical-OMR speed and cost, with AI-grade robustness on the messy real-world marks that traditional tools get wrong.

## What's In The Box

- **Printable A4 answer sheet templates** (PDF + source) in multiple variants:
  - Standard A–E
  - A–D–N
  - Multi-section layouts
  - Two-answer (multi-mark) questions
- **Scanning + marking pipeline** that accepts plain document scanner output
- **CSV / Excel export** with student ID, answers, score, wrong-question list, and ambiguous-mark flags
- **Operator UI** (React) for batch upload, progress monitoring, review queue, and exports
- **Setup guide + sample sheets + accuracy test harness**

## Stack

- **OMR engine:** Python + OpenCV (the deterministic core)
- **AI fallback:** Claude API (`@anthropic-ai/sdk`)
- **Operator UI:** React + TypeScript + Tailwind
- **API layer:** Express (Node) bridging the UI to the Python engine

## Status

This repository currently contains the operator UI scaffold and the Claude vision service. The Python OMR engine, printable templates, scoring, and exports are tracked as separate sections in the implementation plan.
