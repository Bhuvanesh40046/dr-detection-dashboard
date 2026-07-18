const BASE = "/api/predictions";

export async function createPrediction(file) {
  const form = new FormData();
  form.append("image", file);

  const res = await fetch(BASE, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed with status ${res.status}`);
  }
  return res.json();
}

export async function listPredictions(limit = 20, offset = 0) {
  const res = await fetch(`${BASE}?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error("Failed to load history");
  return res.json();
}

export async function getPrediction(id) {
  const res = await fetch(`${BASE}/${id}`);
  if (!res.ok) throw new Error("Failed to load prediction");
  return res.json();
}
