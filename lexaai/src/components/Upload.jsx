import { useState, useRef } from "react";
import { FileUp } from "lucide-react";

export default function UploadZone({ onFileSelect, loading, hasResult}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onFileSelect(file);
  };

  const handleChange = (e) => {
    if (e.target.files[0]) onFileSelect(e.target.files[0]);
    e.target.value = "";
  };

  return (
    <div
      onClick={() => inputRef.current.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`upload-zone ${dragging ? "dragging" : ""} ${loading ? "loading" : ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        className="file-input"
        onChange={handleChange}
      />
      <div className="upload-icon-wrap">
        {loading
          ? <div className="spin" />
          : <FileUp size={25} strokeWidth={1.9} />
        }
      </div>
      <p className="upload-title">
        {loading ? "Analysing contract..." : "Drop your contract here"}
      </p>
      <p className="upload-sub">
        Drag & drop or click to upload
      </p>
      <div className="type-tags">
        <span className="type-tag">PDF</span>
      </div>
    </div>
  );
}
