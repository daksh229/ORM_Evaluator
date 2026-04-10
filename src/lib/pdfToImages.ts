/**
 * Convert a user-uploaded PDF into one PNG File per page using pdfjs-dist
 * in the browser. No backend poppler / pdf2image dependency — the conversion
 * happens before the upload reaches the Node bridge.
 */

import * as pdfjsLib from 'pdfjs-dist';
// Vite resolves the worker at build time and copies it into the bundle.
// @ts-ignore — pdf.worker.min.mjs has no .d.ts shim
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

// PDF.js base resolution is 72 DPI; scale 4 ≈ 288 DPI, close enough to the
// engine's canonical 300 DPI grid that no quality is lost during alignment.
const RENDER_SCALE = 4.0;

async function renderPdfPagesToPng(file: File): Promise<File[]> {
  const arrayBuffer = await file.arrayBuffer();
  const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
  const pdf = await loadingTask.promise;

  const out: File[] = [];
  const baseName = file.name.replace(/\.pdf$/i, '');

  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const viewport = page.getViewport({ scale: RENDER_SCALE });

    const canvas = document.createElement('canvas');
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas 2D context unavailable');

    await page.render({ canvasContext: ctx, viewport }).promise;

    const blob: Blob = await new Promise((resolve, reject) => {
      canvas.toBlob(
        (b) => (b ? resolve(b) : reject(new Error('canvas.toBlob failed'))),
        'image/png',
      );
    });

    out.push(
      new File([blob], `${baseName}_page${pageNum}.png`, { type: 'image/png' }),
    );
  }
  return out;
}

/**
 * Pass-through for image files; PDFs are split into one PNG per page.
 * The engine then sees a flat list of single-page images regardless of
 * whether the operator uploaded a multi-page PDF, a folder of scans, or
 * a camera capture.
 */
export async function expandFiles(files: File[]): Promise<File[]> {
  const out: File[] = [];
  for (const f of files) {
    const isPdf =
      f.type === 'application/pdf' || /\.pdf$/i.test(f.name);
    if (isPdf) {
      try {
        out.push(...(await renderPdfPagesToPng(f)));
      } catch (err) {
        console.error(`Failed to convert PDF ${f.name}:`, err);
      }
    } else {
      out.push(f);
    }
  }
  return out;
}
