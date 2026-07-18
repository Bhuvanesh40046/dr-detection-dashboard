import { formatTime, stageStyle } from "../stageStyles.js";

export default function HistoryList({ items, activeId, onSelect }) {
  if (!items.length) {
    return <div className="empty-state">No predictions yet. Upload an image to get started.</div>;
  }

  return (
    <div>
      {items.map((item) => {
        const label = item.status === "ok" ? item.predicted_class : "Rejected";
        const style = item.status === "ok" ? stageStyle(item.predicted_class) : stageStyle(null);
        return (
          <div
            key={item.id}
            className={`history-item${activeId === item.id ? " active" : ""}`}
            onClick={() => onSelect(item.id)}
          >
            <img src={item.image_path} alt="" className="history-thumb" />
            <div className="history-meta">
              <div className="history-class">{label}</div>
              <div className="history-time">{formatTime(item.created_at)}</div>
            </div>
            <span className="severity-dot" style={{ background: style.dot }} />
          </div>
        );
      })}
    </div>
  );
}
