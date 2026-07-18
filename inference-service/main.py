"""
FastAPI service that exposes the DR detection pipeline over HTTP.
The Express API calls this service; it never talks to torch directly.
"""

import base64
import io

import cv2
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from pipeline import run_inference

app = FastAPI(title="DR Detection Inference Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to the Express API's origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)


def encode_image_to_data_url(rgb_array) -> str:
    """numpy RGB array -> base64 PNG data URL for easy embedding in <img src>."""
    bgr = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
    success, buffer = cv2.imencode(".png", bgr)
    if not success:
        raise RuntimeError("Failed to encode image")
    b64 = base64.b64encode(buffer.tobytes()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    raw = await file.read()
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read image file.")

    result = run_inference(image)

    if result["heatmap_image"] is not None:
        result["heatmap_image"] = encode_image_to_data_url(result["heatmap_image"])
    if result["boxed_image"] is not None:
        result["boxed_image"] = encode_image_to_data_url(result["boxed_image"])

    return result
