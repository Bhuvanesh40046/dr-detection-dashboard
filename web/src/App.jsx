import { useEffect, useState } from "react";
import HistoryList from "./components/HistoryList.jsx";
import ResultView from "./components/ResultView.jsx";
import UploadForm from "./components/UploadForm.jsx";
import { createPrediction, listPredictions } from "./api.js";

export default function App() {
  const [history, setHistory] = useState([]);
  const [selected, setSelected] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function refreshHistory() {
    try {
      const data = await listPredictions();
      setHistory(data.items);
      return data.items;
    } catch (err) {
      setError(err.message);
      return [];
    }
  }

  useEffect(() => {
    refreshHistory().then((items) => {
      if (items.length) setSelected(items[0]);
    });
  }, []);

  async function handleUpload(file) {
    setIsSubmitting(true);
    setError(null);
    try {
      const record = await createPrediction(file);
      setSelected(record);
      await refreshHistory();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSelect(id) {
    const found = history.find((item) => item.id === id);
    if (found) setSelected(found);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" />
          <h1>DR Detection Dashboard</h1>
        </div>
        <span className="subtitle">RBLNet · ResNet18 + attention · Grad-CAM</span>
      </header>

      <div className="app-body">
        <div>
          <div className="panel">
            <p className="panel-title">Upload</p>
            <UploadForm onSubmit={handleUpload} isSubmitting={isSubmitting} />
            {error && (
              <div className="warning-box" style={{ marginTop: 12 }}>
                {error}
              </div>
            )}
          </div>

          <div className="panel">
            <p className="panel-title">History</p>
            <HistoryList items={history} activeId={selected?.id} onSelect={handleSelect} />
          </div>
        </div>

        <div className="panel">
          <ResultView prediction={selected} />
        </div>
      </div>
    </div>
  );
}
