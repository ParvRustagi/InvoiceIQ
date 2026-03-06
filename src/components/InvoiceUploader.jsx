import { useState, useRef, useCallback } from "react";

const ALLOWED_TYPES = ["application/pdf", "image/png", "image/jpeg", "image/jpg", "image/tiff"];
const ALLOWED_EXTENSIONS = ["pdf", "png", "jpg", "jpeg", "tiff"];
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

const TYPE_BADGES = {
  "application/pdf": { label: "PDF", color: "#E53E3E" },
  "image/png": { label: "PNG", color: "#38A169" },
  "image/jpeg": { label: "JPG", color: "#3182CE" },
  "image/jpg": { label: "JPG", color: "#3182CE" },
  "image/tiff": { label: "TIFF", color: "#805AD5" },
};

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function InvoiceUploader({ onUpload, onProgress }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);

  const validateFile = (file) => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
    }
    if (file.size > MAX_SIZE) {
      return `File too large (${formatBytes(file.size)}). Maximum size is 10MB.`;
    }
    return null;
  };

  const handleFile = useCallback((file) => {
    if (!file) return;
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      setSelectedFile(null);
      return;
    }
    setError("");
    setSelectedFile(file);
    onUpload(file);
  }, [onUpload]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  }, [handleFile]);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleInputChange = (e) => {
    handleFile(e.target.files[0]);
  };

  const badge = selectedFile ? TYPE_BADGES[selectedFile.type] : null;

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 480 }}>
      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${isDragging ? "#3182CE" : error ? "#E53E3E" : "#CBD5E0"}`,
          borderRadius: 12,
          padding: "40px 24px",
          textAlign: "center",
          cursor: "pointer",
          background: isDragging ? "#EBF8FF" : "#F7FAFC",
          transition: "all 0.2s",
        }}
      >
        <div style={{ fontSize: 36, marginBottom: 12 }}>📄</div>
        <div style={{ fontWeight: 600, fontSize: 15, color: "#2D3748", marginBottom: 6 }}>
          Drag & drop your invoice here
        </div>
        <div style={{ fontSize: 13, color: "#718096" }}>
          or <span style={{ color: "#3182CE", textDecoration: "underline" }}>browse files</span>
        </div>
        <div style={{ fontSize: 12, color: "#A0AEC0", marginTop: 8 }}>
          PDF, PNG, JPG, TIFF — max 10MB
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.tiff"
          style={{ display: "none" }}
          onChange={handleInputChange}
        />
      </div>

      {/* Error */}
      {error && (
        <div style={{
          marginTop: 10, padding: "10px 14px", borderRadius: 8,
          background: "#FFF5F5", border: "1px solid #FEB2B2",
          color: "#C53030", fontSize: 13
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Selected File Info */}
      {selectedFile && !error && (
        <div style={{
          marginTop: 12, padding: "12px 16px", borderRadius: 10,
          background: "#F0FFF4", border: "1px solid #9AE6B4",
          display: "flex", alignItems: "center", gap: 12
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: 14, color: "#22543D" }}>
              {selectedFile.name}
            </div>
            <div style={{ fontSize: 12, color: "#276749", marginTop: 2 }}>
              {formatBytes(selectedFile.size)}
            </div>
          </div>
          {badge && (
            <span style={{
              background: badge.color, color: "#fff",
              padding: "3px 10px", borderRadius: 20,
              fontSize: 11, fontWeight: 700
            }}>
              {badge.label}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
