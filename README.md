# DR Detection Dashboard

Full-stack wrapper around an existing diabetic retinopathy detection model
(RBLNet: ResNet18 + multi-head attention, originally deployed as a Gradio
Space at `Bhuvi046/dr-detection`). Upload a fundus image, get a DR stage
prediction with a Grad-CAM heatmap and lesion bounding boxes, and browse
prediction history.

## Architecture

```
React (web) → Express API (api) → FastAPI inference service (inference-service)
                    ↓
              PostgreSQL (predictions history)
```

- **inference-service/** — FastAPI wrapper around the original model logic
  (fundus validation, CLAHE preprocessing, RBLNet classification, Grad-CAM,
  lesion detection). Pure Python/torch, no web-app concerns.
- **api/** — Express REST API. Handles uploads, calls the inference service,
  persists results in Postgres, serves image files.
- **web/** — React (Vite) frontend. Upload form, result view, history list.

## Before you run this: one file you need to add

`inference-service/rbl_model.pth` is **not included** — it's the trained
model weight file (46.5 MB) from your Hugging Face Space. Download it and
place it in `inference-service/` before building:

```
https://huggingface.co/spaces/Bhuvi046/dr-detection/resolve/main/rbl_model.pth
```

Everything else (`model.py`, the pipeline logic in `pipeline.py`) is already
adapted from your original `app.py` / `model.py` — same architecture, same
preprocessing, same Grad-CAM logic, just with the Gradio UI replaced by a
`/predict` JSON endpoint.

## Running locally with Docker Compose

```bash
cd dr-dashboard
docker compose up --build
```

Then apply the database migration once (first run only):

```bash
docker compose exec api node src/migrate.js
```

- Frontend: http://localhost:5173
- API: http://localhost:4000
- Inference service: http://localhost:8000/health

## Running without Docker (faster iteration while developing)

**Inference service**
```bash
cd inference-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# place rbl_model.pth here first
uvicorn main:app --reload --port 8000
```

**Postgres** — run it any way you like, then:
```bash
cd api
cp .env.example .env   # edit DATABASE_URL if needed
npm install
npm run migrate
npm run dev
```

**Frontend**
```bash
cd web
npm install
npm run dev
```
Vite's dev server proxies `/api` and `/uploads` to `localhost:4000` (see
`vite.config.js`), so no CORS setup is needed in development.

## API reference

| Method | Path                    | Description                                  |
|--------|-------------------------|-----------------------------------------------|
| POST   | `/api/predictions`      | Upload an image (`multipart/form-data`, field `image`), run inference, persist and return the record |
| GET    | `/api/predictions`      | Paginated history (`?limit=&offset=`), newest first |
| GET    | `/api/predictions/:id`  | Single prediction record                     |

## What's deliberately out of scope

No auth, no job queue, no cloud storage — images live on a local volume and
inference runs synchronously in the request. That's the right call for a
project this size; if you want to talk about how you'd scale it in an
interview, the natural next steps are: a queue (SQS/BullMQ) if inference
latency becomes a problem, S3 instead of local disk, and auth if this ever
stops being a single-user tool.
