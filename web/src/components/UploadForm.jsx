import { useRef, useState } from "react";

export default function UploadForm({ onSubmit, isSubmitting }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  function handleFile(selected) {
    if (!selected) return;
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files?.[0];
    handleFile(dropped);
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;
    onSubmit(file);
  }

  return (
    <form onSubmit={handleSubmit}>
      <div
        className={`dropzone${dragging ? " dragging" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        {previewUrl ? (
          <img src={previewUrl} alt="Selected fundus image" className="preview-thumb" />
        ) : null}
        <div>
          {file ? file.name : "Drop a fundus image here, or click to browse"}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>

      <button
        type="submit"
        className="btn btn-primary"
        disabled={!file || isSubmitting}
        style={{ marginTop: 14 }}
      >
        {isSubmitting ? "Analyzing…" : "Analyze image"}
      </button>
    </form>
  );
}
