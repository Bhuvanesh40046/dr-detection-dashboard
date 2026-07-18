export const STAGE_STYLES = {
  "No DR": { text: "#0a5747", bg: "#e3f2ee", dot: "#0e7c66" },
  "Mild NPDR": { text: "#5c6b17", bg: "#f2f5e3", dot: "#8a9a2e" },
  "Moderate NPDR": { text: "#8a5c0d", bg: "#faf0dd", dot: "#c8951e" },
  "Severe NPDR": { text: "#8f4419", bg: "#f9ebe1", dot: "#c2612c" },
  "Proliferative DR": { text: "#7a2323", bg: "#fbeaea", dot: "#b23a3a" },
};

export function stageStyle(label) {
  return STAGE_STYLES[label] || { text: "#16232b", bg: "#f2f5f4", dot: "#5b6b70" };
}

export function formatPct(value) {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
