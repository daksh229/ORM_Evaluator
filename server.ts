import express from "express";
import { createServer as createViteServer } from "vite";
import path from "path";
import fs from "fs";
import multer from "multer";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  // Configure Multer for image uploads
  const storage = multer.memoryStorage();
  const upload = multer({ limits: { fileSize: 10 * 1024 * 1024 } }); // 10MB limit

  app.use(express.json());

  // API Routes
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok" });
  });

  // Forward scans to the Python OMR engine. The Node server is just the
  // operator-facing bridge — it does no CV work itself.
  const OMR_ENGINE_URL = process.env.OMR_ENGINE_URL || "http://localhost:8000";

  app.post("/api/process-scan", upload.single("file"), async (req: any, res) => {
    try {
      if (!req.file) {
        return res.status(400).json({ error: "No file uploaded" });
      }

      const templateId: string = req.body?.template_id || "AE_SAMPLE_5Q";

      const formData = new FormData();
      const blob = new Blob([req.file.buffer], {
        type: req.file.mimetype || "application/octet-stream",
      });
      formData.append("file", blob, req.file.originalname || "scan.png");
      formData.append("template_id", templateId);

      const upstream = await fetch(`${OMR_ENGINE_URL}/process`, {
        method: "POST",
        body: formData,
      });

      if (!upstream.ok) {
        const text = await upstream.text();
        return res
          .status(upstream.status)
          .json({ error: `OMR engine error: ${text}` });
      }

      const result = await upstream.json();
      res.json(result);
    } catch (error) {
      console.error("Processing error:", error);
      res.status(500).json({ error: "Failed to process scan" });
    }
  });

  // --- Sessions / templates / answer-keys / exports proxy ---
  // The Node bridge stays a thin proxy: all OMR domain logic lives in the
  // Python engine. These routes just forward calls and stream the response.

  async function proxyToEngine(
    targetPath: string,
    res: any,
    init?: RequestInit,
  ) {
    try {
      const upstream = await fetch(`${OMR_ENGINE_URL}${targetPath}`, init);
      const ct = upstream.headers.get("content-type") || "application/octet-stream";
      const cd = upstream.headers.get("content-disposition");
      res.status(upstream.status);
      res.setHeader("content-type", ct);
      if (cd) res.setHeader("content-disposition", cd);
      const buf = Buffer.from(await upstream.arrayBuffer());
      res.send(buf);
    } catch (err) {
      console.error("Proxy error:", err);
      res.status(502).json({ error: "OMR engine unreachable" });
    }
  }

  app.get("/api/templates", (_req, res) => proxyToEngine("/templates", res));

  // Serve a template's printable PDF directly from omr_engine/templates/.
  app.get("/api/templates/:id/pdf", (req, res) => {
    const id = req.params.id;
    if (!/^[A-Za-z0-9_]+$/.test(id)) {
      return res.status(400).json({ error: "Invalid template id" });
    }
    const pdfPath = path.join(process.cwd(), "omr_engine", "templates", `${id}.pdf`);
    if (!fs.existsSync(pdfPath)) {
      return res
        .status(404)
        .json({ error: `Template PDF not found: ${id}.pdf — run python -m omr_engine.pdf.generate` });
    }
    res.setHeader("content-type", "application/pdf");
    res.setHeader("content-disposition", `attachment; filename="${id}.pdf"`);
    fs.createReadStream(pdfPath).pipe(res);
  });
  app.get("/api/answer-keys", (_req, res) => proxyToEngine("/answer-keys", res));

  app.get("/api/sessions", (_req, res) => proxyToEngine("/sessions", res));

  app.get("/api/sessions/:id", (req, res) =>
    proxyToEngine(`/sessions/${encodeURIComponent(req.params.id)}`, res),
  );

  app.get("/api/sessions/:id/export.csv", (req, res) =>
    proxyToEngine(
      `/sessions/${encodeURIComponent(req.params.id)}/export.csv`,
      res,
    ),
  );

  app.get("/api/sessions/:id/export.xlsx", (req, res) =>
    proxyToEngine(
      `/sessions/${encodeURIComponent(req.params.id)}/export.xlsx`,
      res,
    ),
  );

  // Create a session — multipart form fields, no files.
  app.post("/api/sessions", upload.none(), async (req: any, res) => {
    const fd = new FormData();
    for (const [k, v] of Object.entries(req.body || {})) {
      fd.append(k, String(v));
    }
    await proxyToEngine("/sessions", res, { method: "POST", body: fd });
  });

  // Add one scan to an existing session — multipart with file + optional fields.
  app.post(
    "/api/sessions/:id/scans",
    upload.single("file"),
    async (req: any, res) => {
      if (!req.file) {
        return res.status(400).json({ error: "No file uploaded" });
      }
      const fd = new FormData();
      const blob = new Blob([req.file.buffer], {
        type: req.file.mimetype || "application/octet-stream",
      });
      fd.append("file", blob, req.file.originalname || "scan.png");
      if (req.body?.student_name) {
        fd.append("student_name", String(req.body.student_name));
      }
      await proxyToEngine(
        `/sessions/${encodeURIComponent(req.params.id)}/scans`,
        res,
        { method: "POST", body: fd },
      );
    },
  );

  // Manually override a single box's classification (Review Queue → Section I2).
  app.patch(
    "/api/sessions/:sid/sheets/:shid/boxes/:idx",
    async (req: any, res) => {
      const { sid, shid, idx } = req.params;
      const status = (req.query.status as string) || "";
      if (!status) {
        return res
          .status(400)
          .json({ error: "Missing 'status' query parameter" });
      }
      await proxyToEngine(
        `/sessions/${encodeURIComponent(sid)}/sheets/${encodeURIComponent(shid)}/boxes/${encodeURIComponent(idx)}?status=${encodeURIComponent(status)}`,
        res,
        { method: "PATCH" },
      );
    },
  );

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
