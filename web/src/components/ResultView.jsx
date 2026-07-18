import { formatPct, stageStyle } from "../stageStyles.js";

export default function ResultView({ prediction }) {
  if (!prediction) {
    return <div className="empty-state">Select a prediction, or upload a new fundus image.</div>;
  }

  if (prediction.status === "rejected") {
    return (
      <div>
        <div className="warning-box">
          <strong>Input rejected.</strong> {prediction.message}
        </div>
        <p style={{ color: "var(--ink-muted)", fontSize: 13 }}>
          This tool only analyzes retinal fundus photographs. Upload a fundus image to run
          diabetic retinopathy staging.
        </p>
      </div>
    );
  }

  const style = stageStyle(prediction.predicted_class);
  const confidences = prediction.all_confidences || {};
  const lesions = prediction.lesions || [];

  return (
    <div>
      <div className="stage-banner" style={{ background: style.bg, color: style.text }}>
        <div>
          <p className="stage-name">{prediction.predicted_class}</p>
          <p className="stage-note">{prediction.diagnosis_note}</p>
        </div>
        <div className="stage-confidence">{formatPct(prediction.confidence)}</div>
      </div>

      {prediction.is_low_confidence && (
        <div className="warning-box">
          Low-confidence prediction (below 40% threshold). Recommend retaking the image or
          consulting a specialist directly.
        </div>
      )}

      {prediction.uncertainty_warning && (
        <div className="warning-box">{prediction.uncertainty_warning}</div>
      )}

      <div className="image-grid">
        <div className="image-card">
          <img src={prediction.heatmap_path} alt="Grad-CAM heatmap" />
          <div className="image-card-label">Grad-CAM heatmap</div>
        </div>
        <div className="image-card">
          <img src={prediction.boxed_path} alt="Lesion bounding boxes" />
          <div className="image-card-label">Lesion regions</div>
        </div>
      </div>

      <p className="panel-title">Stage probabilities</p>
      {Object.entries(confidences)
        .sort((a, b) => b[1] - a[1])
        .map(([label, value]) => (
          <div className="confidence-row" key={label}>
            <span>{label}</span>
            <div className="confidence-track">
              <div className="confidence-fill" style={{ width: `${value * 100}%` }} />
            </div>
            <span className="confidence-value">{formatPct(value)}</span>
          </div>
        ))}

      <p className="panel-title" style={{ marginTop: 20 }}>
        Detected lesions
      </p>
      {lesions.length ? (
        <table className="lesion-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Type</th>
              <th>Bounding box (x1, y1, x2, y2)</th>
            </tr>
          </thead>
          <tbody>
            {lesions.map((lesion, i) => (
              <tr key={i}>
                <td>{i + 1}</td>
                <td>{lesion.type}</td>
                <td className="mono">{lesion.bbox.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p style={{ fontSize: 13, color: "var(--ink-muted)" }}>
          No focal lesions detected by Grad-CAM.
        </p>
      )}

      <p className="disclaimer">
        For research and educational purposes only. Not a medical device and not a substitute
        for professional diagnosis. Consult a qualified ophthalmologist for any concerns about
        eye health.
      </p>
    </div>
  );
}
