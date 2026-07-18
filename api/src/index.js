import path from "node:path";
import "dotenv/config";
import cors from "cors";
import express from "express";
import predictionsRouter from "./routes/predictions.js";

const app = express();
const PORT = process.env.PORT || 4000;
const UPLOAD_DIR = process.env.UPLOAD_DIR || path.resolve("uploads");

app.use(cors());
app.use(express.json());
app.use("/uploads", express.static(UPLOAD_DIR));

app.get("/health", (req, res) => res.json({ status: "ok" }));
app.use("/api/predictions", predictionsRouter);

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: "Internal server error" });
});

app.listen(PORT, () => {
  console.log(`API listening on port ${PORT}`);
});
