"""
DR detection inference pipeline.

This is the original Bhuvi046/dr-detection logic (fundus validation, CLAHE
preprocessing, RBLNet classification, Grad-CAM heatmap, lesion bounding boxes)
with the Gradio UI removed. main.py wraps this in a FastAPI endpoint.
"""

import cv2
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image, ImageOps
from pytorch_grad_cam import GradCAM

from model import RBLNet

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = RBLNet(num_classes=5, pretrained=False).to(device)
model.load_state_dict(torch.load("rbl_model.pth", map_location=device))
model.eval()

target_layer = model.backbone.layer4[-1]

transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
])

CLASSES = [
    "No DR",
    "Mild NPDR",
    "Moderate NPDR",
    "Severe NPDR",
    "Proliferative DR",
]

STAGE_DESCRIPTIONS = {
    0: "No signs of diabetic retinopathy detected.",
    1: "Mild non-proliferative DR: small microaneurysms present.",
    2: "Moderate non-proliferative DR: more microaneurysms, hemorrhages, and possible exudates.",
    3: "Severe non-proliferative DR: extensive hemorrhages and vascular changes. Urgent referral recommended.",
    4: "Proliferative DR: abnormal blood vessel growth. Sight-threatening — immediate specialist care needed.",
}

LOW_CONFIDENCE_THRESHOLD = 0.40


# -----------------------------------------------------------------------------
# Step 1: Fundus image validation
# -----------------------------------------------------------------------------
def is_fundus_image(pil_img):
    """Heuristic check that distinguishes real fundus photos from visually
    similar but unrelated inputs (moons, light bulbs, orange fruit, etc.)."""
    img = np.array(pil_img.convert("RGB").resize((224, 224))).astype(np.float32)
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]

    gray = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    mask = gray > 20
    if mask.sum() < 2000:
        return False, "Not a fundus image: no bright region detected."

    mean_r = r[mask].mean()
    mean_g = g[mask].mean()
    mean_b = b[mask].mean()

    if mean_g < 1 or mean_b < 1:
        return False, "Not a fundus image: unusual color profile."

    r_to_g = mean_r / mean_g
    r_to_b = mean_r / mean_b

    if r_to_g < 1.25:
        return False, (
            f"Not a fundus image: colors look grayscale "
            f"(R/G ratio = {r_to_g:.2f}, expected > 1.25)."
        )
    if r_to_b < 1.8:
        return False, (
            f"Not a fundus image: too much blue content "
            f"(R/B ratio = {r_to_b:.2f}, expected > 1.8)."
        )
    if mean_b > 120:
        return False, (
            f"Not a fundus image: blue channel too bright "
            f"(mean = {mean_b:.0f}, expected < 120)."
        )

    gray_full = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    h, w = gray_full.shape
    cs = 25
    corner_mean = np.mean([
        gray_full[:cs, :cs].mean(),
        gray_full[:cs, -cs:].mean(),
        gray_full[-cs:, :cs].mean(),
        gray_full[-cs:, -cs:].mean(),
    ])
    center_mean = gray_full[h // 3:2 * h // 3, w // 3:2 * w // 3].mean()
    if corner_mean > 80 or center_mean < corner_mean + 20:
        return False, "Not a fundus image: no dark border / bright circular region."

    g_channel = img[:, :, 1].astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    blackhat = cv2.morphologyEx(g_channel, cv2.MORPH_BLACKHAT, kernel)
    vessel_pixels = (blackhat > 15) & mask
    vessel_ratio = vessel_pixels.sum() / max(mask.sum(), 1)

    if vessel_ratio < 0.015:
        return False, (
            f"Not a fundus image: no blood vessels detected "
            f"(vessel score = {vessel_ratio:.3f}, expected > 0.015)."
        )

    return True, f"Valid fundus image (R/G={r_to_g:.2f}, vessels={vessel_ratio:.3f})"


# -----------------------------------------------------------------------------
# Step 2: Preprocessing — circular crop + CLAHE
# -----------------------------------------------------------------------------
def crop_to_fundus(img_np):
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img_np
    x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
    return img_np[y:y + h, x:x + w]


def apply_clahe(img_np):
    lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)


def preprocess_fundus(pil_img):
    pil_img = ImageOps.exif_transpose(pil_img).convert("RGB")
    img_np = np.array(pil_img)
    img_np = crop_to_fundus(img_np)
    img_np = apply_clahe(img_np)
    return Image.fromarray(img_np)


# -----------------------------------------------------------------------------
# Step 3: Lesion type classification (heuristic)
# -----------------------------------------------------------------------------
def classify_lesion(crop_rgb):
    if crop_rgb.size == 0 or crop_rgb.shape[0] < 3 or crop_rgb.shape[1] < 3:
        return "Unknown"

    hsv = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    r, g, b = crop_rgb[:, :, 0], crop_rgb[:, :, 1], crop_rgb[:, :, 2]

    mean_v = v.mean()
    yellow_ratio = ((h > 15) & (h < 40) & (s > 80) & (v > 120)).mean()
    white_ratio = ((v > 180) & (s < 60)).mean()
    dark_red_ratio = ((r > 50) & (g < 90) & (b < 90) & (r.astype(int) - g.astype(int) > 20)).mean()
    area = crop_rgb.shape[0] * crop_rgb.shape[1]

    if yellow_ratio > 0.2 and mean_v > 120:
        return "Hard Exudate"
    if white_ratio > 0.25 and s.mean() < 70:
        return "Soft Exudate"
    if dark_red_ratio > 0.25 and area < 250:
        return "Microaneurysm"
    if dark_red_ratio > 0.15:
        return "Hemorrhage"
    return "Suspicious Lesion"


# -----------------------------------------------------------------------------
# Step 4: Grad-CAM + bounding boxes + lesion type labels
# -----------------------------------------------------------------------------
def generate_visualization(pil_img_processed):
    """Returns (heatmap_overlay_rgb, boxed_image_rgb, lesions_list)."""
    img_resized = pil_img_processed.resize((224, 224))
    input_tensor = transform(pil_img_processed).unsqueeze(0).to(device)

    torch.set_grad_enabled(True)
    cam = GradCAM(model=model, target_layers=[target_layer])
    grayscale_cam = cam(input_tensor=input_tensor)[0]
    torch.set_grad_enabled(False)

    heatmap_color = cv2.applyColorMap(np.uint8(255 * grayscale_cam), cv2.COLORMAP_JET)
    heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
    img_np = np.array(img_resized)
    overlay = cv2.addWeighted(img_np, 0.55, heatmap_color, 0.45, 0)

    heat = cv2.GaussianBlur(grayscale_cam, (7, 7), 0)
    heat = (heat > 0.80).astype(np.uint8) * 255
    kernel = np.ones((3, 3), np.uint8)
    heat = cv2.morphologyEx(heat, cv2.MORPH_CLOSE, kernel)
    heat = cv2.morphologyEx(heat, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(heat, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    boxed_img = img_np.copy()
    lesions = []
    img_area = 224 * 224

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if area < 120 or area > 0.30 * img_area:
            continue

        crop = img_np[y:y + h, x:x + w]
        lesion_type = classify_lesion(crop)
        lesions.append({
            "type": lesion_type,
            "bbox": [int(x), int(y), int(x + w), int(y + h)],
        })

        color = (216, 90, 48)  # single consistent box color for the API/UI to theme
        cv2.rectangle(boxed_img, (x, y), (x + w, y + h), color, 2)
        label = lesion_type
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        label_y = max(y - 5, th + 2)
        cv2.rectangle(boxed_img, (x, label_y - th - 2), (x + tw + 4, label_y + 2), color, -1)
        cv2.putText(boxed_img, label, (x + 2, label_y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, (255, 255, 255), 1, cv2.LINE_AA)

    return overlay, boxed_img, lesions


# -----------------------------------------------------------------------------
# Step 5: Main predict function
# -----------------------------------------------------------------------------
def run_inference(image: Image.Image) -> dict:
    """Runs the full pipeline on a PIL image and returns a JSON-serializable dict.

    Callers (the FastAPI route) are responsible for encoding heatmap_image /
    boxed_image (numpy arrays, RGB) to base64 PNG before sending to the client.
    """
    valid, msg = is_fundus_image(image)
    if not valid:
        return {
            "status": "rejected",
            "message": msg,
            "predicted_class": None,
            "confidence": None,
            "top2_class": None,
            "top2_confidence": None,
            "is_low_confidence": False,
            "diagnosis_note": None,
            "lesions": [],
            "heatmap_image": None,
            "boxed_image": None,
        }

    processed = preprocess_fundus(image)

    input_tensor = transform(processed).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(input_tensor)
        probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

    top1_idx = int(np.argmax(probs))
    top1_conf = float(probs[top1_idx])
    sorted_idx = np.argsort(probs)[::-1]
    top2_idx = int(sorted_idx[1])
    top2_conf = float(probs[top2_idx])

    is_low_confidence = top1_conf < LOW_CONFIDENCE_THRESHOLD
    heat_img, boxed_img, lesions = generate_visualization(processed)

    diagnosis_note = STAGE_DESCRIPTIONS[top1_idx]
    uncertainty_warning = None
    if {top1_idx, top2_idx} == {3, 4} and abs(top1_conf - top2_conf) < 0.20:
        uncertainty_warning = (
            "Model is torn between Severe NPDR and Proliferative DR. Both indicate "
            "advanced disease requiring urgent specialist referral."
        )

    return {
        "status": "ok",
        "message": "Prediction complete.",
        "predicted_class": CLASSES[top1_idx],
        "confidence": top1_conf,
        "top2_class": CLASSES[top2_idx],
        "top2_confidence": top2_conf,
        "is_low_confidence": is_low_confidence,
        "diagnosis_note": diagnosis_note,
        "uncertainty_warning": uncertainty_warning,
        "all_confidences": {CLASSES[i]: float(probs[i]) for i in range(5)},
        "lesions": lesions,
        "heatmap_image": heat_img,   # numpy array, encoded by the route
        "boxed_image": boxed_img,    # numpy array, encoded by the route
    }
