# DR Detection Dashboard

A full-stack web application for diabetic retinopathy screening. Upload a
retinal fundus image and get a DR stage prediction (0–4), a Grad-CAM heatmap
showing which regions influenced the model, detected lesion bounding boxes,
and a searchable history of past predictions — all backed by a real
diagnostic model, not a placeholder.

<!-- Add a screenshot of the dashboard here, e.g. ![Dashboard screenshot](docs/screenshot.png) -->

## What this demonstrates

This isn't a CRUD to-do app — it's infrastructure around a real computer
vision model:

- **Frontend (React):** drag-and-drop upload, a result view rendering
  model output (confidence bars, Grad-CAM overlay, lesion table), and a
  persistent history sidebar.
- **Backend (Node/Express):** REST API orchestrating the request lifecycle —
  receives the upload, calls the inference service, persists structured
  results, serves generated images.
- **Database (PostgreSQL):** relational schema with a JSONB column for the
  model's variable-length lesion output, indexed for the history query.
- **ML service (FastAPI/PyTorch):** the model itself — a ResNet18 backbone
  with a multi-head attention layer (RBLNet), Grad-CAM for explainability,
  and input validation (rejects non-fundus images) plus confidence-based
  abstention on uncertain predictions.
- **Deployment:** four containerized services (Postgres, inference, API,
  web) orchestrated with Docker Compose, with nginx reverse-proxying the
  frontend to the API in production.

The model (RBLNet: ResNet18 + multi-head attention) was originally trained
and deployed as a standalone Gradio Space; this project wraps it in a
production-shaped full-stack architecture.

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

`inference-service/rbl_model.pth` is **not included in this repo** (46.5 MB
binary, excluded via `.gitignore`). Download it from the model's original
Hugging Face Space and place it in `inference-service/` before building:

```
https://huggingface.co/spaces/Bhuvi046/dr-detection/resolve/main/rbl_model.pth
```

`model.py` and the pipeline logic in `pipeline.py` are adapted from that
Space's original `app.py` / `model.py` — same architecture, same
preprocessing, same Grad-CAM logic, with the Gradio UI replaced by a
`/predict` JSON endpoint so it can be called from the Express API.

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

## License

MIT
