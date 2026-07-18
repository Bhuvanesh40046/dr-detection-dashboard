import { randomUUID } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { Router } from "express";
import FormData from "form-data";
import multer from "multer";
import fetch from "node-fetch";
import pool from "../db.js";

const router = Router();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 15 * 1024 * 1024 } });

const UPLOAD_DIR = process.env.UPLOAD_DIR || path.resolve("uploads");
const INFERENCE_URL = process.env.INFERENCE_URL || "http://localhost:8000";

for (const sub of ["originals", "heatmaps", "boxed"]) {
  fs.mkdirSync(path.join(UPLOAD_DIR, sub), { recursive: true });
}

function dataUrlToBuffer(dataUrl) {
  const base64 = dataUrl.split(",")[1];
  return Buffer.from(base64, "base64");
}

function saveBuffer(subdir, filename, buffer) {
  const filePath = path.join(UPLOAD_DIR, subdir, filename);
  fs.writeFileSync(filePath, buffer);
  return `/uploads/${subdir}/${filename}`;
}

// POST /api/predictions — upload an image, run inference, persist the result
router.post("/", upload.single("image"), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: "No image uploaded. Use the 'image' form field." });
  }

  const id = randomUUID();
  const ext = path.extname(req.file.originalname) || ".png";

  try {
    // 1. Save the original upload
    const originalPath = saveBuffer("originals", `${id}${ext}`, req.file.buffer);

    // 2. Forward to the Python inference service
    const form = new FormData();
    form.append("file", req.file.buffer, {
      filename: req.file.originalname,
      contentType: req.file.mimetype,
    });

    const inferenceRes = await fetch(`${INFERENCE_URL}/predict`, {
      method: "POST",
      body: form,
      headers: form.getHeaders(),
    });

    if (!inferenceRes.ok) {
      const detail = await inferenceRes.text();
      return res.status(502).json({ error: "Inference service error", detail });
    }

    const result = await inferenceRes.json();

    // 3. Save heatmap / boxed images (if the image passed fundus validation)
    let heatmapPath = null;
    let boxedPath = null;
    if (result.status === "ok") {
      heatmapPath = saveBuffer("heatmaps", `${id}.png`, dataUrlToBuffer(result.heatmap_image));
      boxedPath = saveBuffer("boxed", `${id}.png`, dataUrlToBuffer(result.boxed_image));
    }

    // 4. Persist the record
    const insertResult = await pool.query(
      `INSERT INTO predictions (
        original_filename, image_path, heatmap_path, boxed_path,
        status, message, predicted_class, confidence,
        top2_class, top2_confidence, is_low_confidence,
        diagnosis_note, uncertainty_warning, all_confidences, lesions
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
      RETURNING *`,
      [
        req.file.originalname,
        originalPath,
        heatmapPath,
        boxedPath,
        result.status,
        result.message,
        result.predicted_class,
        result.confidence,
        result.top2_class,
        result.top2_confidence,
        result.is_low_confidence,
        result.diagnosis_note,
        result.uncertainty_warning || null,
        result.all_confidences ? JSON.stringify(result.all_confidences) : null,
        result.lesions ? JSON.stringify(result.lesions) : null,
      ]
    );

    res.status(201).json(insertResult.rows[0]);
  } catch (err) {
    console.error("Prediction failed:", err);
    res.status(500).json({ error: "Prediction failed", detail: err.message });
  }
});

// GET /api/predictions — paginated history, newest first
router.get("/", async (req, res) => {
  const limit = Math.min(parseInt(req.query.limit, 10) || 20, 100);
  const offset = parseInt(req.query.offset, 10) || 0;

  try {
    const result = await pool.query(
      `SELECT * FROM predictions ORDER BY created_at DESC LIMIT $1 OFFSET $2`,
      [limit, offset]
    );
    const countResult = await pool.query(`SELECT COUNT(*)::int AS total FROM predictions`);
    res.json({ items: result.rows, total: countResult.rows[0].total, limit, offset });
  } catch (err) {
    console.error("Failed to list predictions:", err);
    res.status(500).json({ error: "Failed to list predictions" });
  }
});

// GET /api/predictions/:id — single record
router.get("/:id", async (req, res) => {
  try {
    const result = await pool.query(`SELECT * FROM predictions WHERE id = $1`, [req.params.id]);
    if (result.rows.length === 0) {
      return res.status(404).json({ error: "Prediction not found" });
    }
    res.json(result.rows[0]);
  } catch (err) {
    console.error("Failed to fetch prediction:", err);
    res.status(500).json({ error: "Failed to fetch prediction" });
  }
});

export default router;
