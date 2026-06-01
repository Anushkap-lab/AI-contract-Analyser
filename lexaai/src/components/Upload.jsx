import { useState, useRef } from "react";
import { Upload } from "lucide-react";

export default function UploadZone({ onFileSelect, isLoading }) {
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
  };

  return (
    <div
      onClick={() => inputRef.current.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`
        min-h-72 border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all
        flex flex-col items-center justify-center
        ${dragging ? "border-gold bg-gold/5" : "border-gray-200 dark:border-gray-700 hover:border-gray-400"}
        ${isLoading ? "opacity-60 pointer-events-none" : ""}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        className="hidden"
        onChange={handleChange}
      />
      <div className="w-12 h-12 bg-navy rounded-xl flex items-center justify-center mb-4">
        {isLoading
          ? <div className="w-5 h-5 border-2 border-gold border-t-transparent rounded-full animate-spin" />
          : <Upload className="text-gold" size={20} />
        }
      </div>
      <p className="font-serif text-base font-medium mb-1">
        {isLoading ? "Analysing contract..." : "Drop your contract here"}
      </p>
      <p className="text-sm text-gray-500">PDF</p>
     
    </div>
  );
}
