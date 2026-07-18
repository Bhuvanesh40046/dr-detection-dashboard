# DR Detection Dashboard

I already had a diabetic retinopathy detection model (RBLNet — ResNet18 backbone
with a multi-head attention layer) running as a Gradio Space. It could classify
fundus images into DR stages, generate Grad-CAM heatmaps, and flag lesion
regions. But it was just a script behind a Gradio UI — no database, no history,
no separation between the model and the app around it.

So I rebuilt it as an actual full-stack app: React frontend, Node/Express API,
PostgreSQL for prediction history, and the original model logic wrapped in a
FastAPI service. The point wasn't to build another to-do app to learn React —
it was to put real infrastructure around a model I'd already trained.

![Dashboard screenshot](docs/screenshot.png)

## How it works

You upload a fundus image from the browser. React sends it to the Express API,
which forwards it to a Python service running the model. That service does the
actual work — checks the image is even a real fundus photo (rejects things like
random objects or non-retina photos), runs CLAHE preprocessing, classifies the
DR stage, generates a Grad-CAM heatmap, and finds lesion bounding boxes. Express
saves the images and the structured result to Postgres, and sends everything
back to React to render.

Splitting it this way was a deliberate call, not the default — Node has no real
equivalent to torch or pytorch-grad-cam, so trying to port the model logic into
JavaScript wasn't realistic. Keeping the model in Python and using Express purely
as an orchestrator (upload → call inference → persist → return) kept each piece
doing one job.

## Stack

- **React (Vite)** — upload form, result view, prediction history
- **Node/Express** — REST API, handles uploads, talks to Postgres and the inference service
- **PostgreSQL** — stores prediction history; lesions are stored as JSONB since it's a variable-length list I don't need to query into
- **FastAPI + PyTorch** — the actual model, unchanged from the original Space, just with the Gradio UI swapped for a `/predict` endpoint
- **Docker Compose** — all four services run together, with nginx handling the frontend's API proxying in production

## Some things I ran into building this

Torch's default PyPI wheel bundles CUDA and is huge — my Docker build kept
timing out on `pip install` because of it. Fixed it by pulling torch/torchvision
from PyTorch's CPU-only wheel index instead, which is a fraction of the size.

Vite's dev server proxies `/api` calls to the backend automatically, but that
proxy only exists in `npm run dev` — it doesn't carry over to the production
Docker build, where the frontend is just static files served by nginx. Had to
add an nginx config that proxies `/api` and `/uploads` to the API container by
service name, or the built frontend would've had no way to reach the backend.

## Running it

You'll need one file that isn't in this repo: `inference-service/rbl_model.pth`
(46.5 MB, excluded via `.gitignore`). Grab it from the original Space and drop
it in `inference-service/`:

```
https://huggingface.co/spaces/Bhuvi046/dr-detection/resolve/main/rbl_model.pth
```

Then:

```bash
docker compose up --build
docker compose exec api node src/migrate.js   # first run only
```

- Frontend: http://localhost:5173
- API: http://localhost:4000
- Inference service: http://localhost:8000/health

### Running without Docker

**Inference service**
```bash
cd inference-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# place rbl_model.pth here first
uvicorn main:app --reload --port 8000
```

**API** (needs Postgres running somewhere)
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

## API

| Method | Path                    | Description                                  |
|--------|-------------------------|-----------------------------------------------|
| POST   | `/api/predictions`      | Upload an image (`multipart/form-data`, field `image`), run inference, persist and return the record |
| GET    | `/api/predictions`      | Paginated history (`?limit=&offset=`), newest first |
| GET    | `/api/predictions/:id`  | Single prediction record                     |

## What I left out on purpose

No auth, no job queue, no S3 — images sit on a local volume and inference runs
synchronously inside the request. For a single-user project this size, adding
those would've been over-engineering. If this needed to handle real traffic,
the next steps would be a queue for inference (so uploads don't block on a
slow prediction), object storage instead of local disk, and auth.

## License

MIT
