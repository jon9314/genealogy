import { ChangeEvent, useEffect, useState } from "react";

import FileCard from "../components/FileCard";
import { deleteSource, listSources, runOCR, uploadFiles } from "../lib/api";
import type { Source } from "../lib/types";

export default function Upload() {
  const [sources, setSources] = useState<Source[]>([]);
  const [busyIds, setBusyIds] = useState<number[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    refresh();
  }, []);

  const refresh = async () => {
    const data = await listSources();
    setSources(data);
  };

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    try {
      setIsUploading(true);
      await uploadFiles(files);
      await refresh();
    } catch (error) {
      console.error("Failed to upload files", error);
      window.alert("Failed to upload files. Please try again.");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this PDF and related records?")) return;
    await deleteSource(id);
    await refresh();
  };

  const handleOCR = async (id: number) => {
    setBusyIds((prev) => [...prev, id]);
    try {
      await runOCR(id);
      await refresh();
    } finally {
      setBusyIds((prev) => prev.filter((value) => value !== id));
    }
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <h2>Upload descendancy PDFs</h2>
        <p>Select one or more PDF files. They are stored locally in ./data/uploads.</p>
        <input type="file" multiple accept="application/pdf" onChange={handleUpload} disabled={isUploading} />
        {isUploading && <p>Uploading…</p>}
      </div>
      <div className="grid two">
        {sources.map((source) => (
          <FileCard
            key={source.id}
            source={source}
            onDelete={handleDelete}
            onRunOCR={handleOCR}
            busy={busyIds.includes(source.id)}
          />
        ))}
        {!sources.length && <p>No files uploaded yet.</p>}
      </div>
    </div>
  );
}

