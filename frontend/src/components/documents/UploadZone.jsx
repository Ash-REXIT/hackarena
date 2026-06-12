import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { FileUp, Upload } from "lucide-react";

const ACCEPT = ".txt,.md,.pdf,.docx";

export default function UploadZone({ onUpload }) {
  const [drag, setDrag] = useState(false);
  const [status, setStatus] = useState("");

  const handleFiles = useCallback(
    async (files) => {
      const file = files?.[0];
      if (!file) return;
      setStatus(`Uploading ${file.name}…`);
      try {
        await onUpload(file);
        setStatus(`Uploaded ${file.name}`);
      } catch (err) {
        setStatus(err.message);
      }
    },
    [onUpload]
  );

  return (
    <div className="space-y-3">
      <motion.div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={`card border-2 border-dashed p-12 text-center transition-colors ${
          drag ? "border-accent bg-accent/5" : "border-border-light"
        }`}
      >
        <Upload className="w-10 h-10 mx-auto mb-4 text-accent/60" />
        <p className="text-gray-300 mb-1">Drag and drop files here</p>
        <p className="text-sm text-gray-500 mb-4">PDF · DOCX · TXT</p>
        <label className="btn-secondary cursor-pointer">
          <FileUp className="w-4 h-4" /> Browse Files
          <input
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </label>
      </motion.div>
      {status && <p className="text-sm text-gray-400">{status}</p>}
    </div>
  );
}
