import { ChangeEvent, useEffect, useState } from "react";

import FileCard from "../components/FileCard";
import { deleteSource, listSources, runOCR, uploadFiles } from "../lib/api";
import type { Source } from "../lib/types";

export default function Upload() {
  const [sources, setSources] = useState<Source[]>([]);
  const [busyIds, setBusyIds] = useState<number[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [batchMode, setBatchMode] = useState(false);

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

  const handleSelect = (id: number, selected: boolean) => {
    setSelectedIds((prev) =>
      selected ? [...prev, id] : prev.filter((value) => value !== id)
    );
  };

  const handleSelectAll = () => {
    if (selectedIds.length === sources.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(sources.map((s) => s.id));
    }
  };

  const handleBatchOCR = async () => {
    if (!selectedIds.length) return;
    setBusyIds(selectedIds);
    try {
      for (const id of selectedIds) {
        try {
          await runOCR(id);
        } catch (error) {
          console.error(`Failed to run OCR for source ${id}:`, error);
        }
      }
      await refresh();
    } finally {
      setBusyIds([]);
      setSelectedIds([]);
    }
  };

  const handleBatchDelete = async () => {
    if (!selectedIds.length) return;
    if (!window.confirm(`Delete ${selectedIds.length} source(s) and related records?`)) return;

    for (const id of selectedIds) {
      try {
        await deleteSource(id);
      } catch (error) {
        console.error(`Failed to delete source ${id}:`, error);
      }
    }
    await refresh();
    setSelectedIds([]);
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <h2>Upload descendancy PDFs</h2>
        <p>Select one or more PDF files. They are stored locally in ./data/uploads.</p>
        <input type="file" multiple accept="application/pdf" onChange={handleUpload} disabled={isUploading} />
        {isUploading && <p>Uploading…</p>}
      </div>

      {sources.length > 0 && (
        <div className="card" style={{ display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
          <button
            className={`btn ${batchMode ? "" : "secondary"}`}
            onClick={() => {
              setBatchMode(!batchMode);
              setSelectedIds([]);
            }}
          >
            {batchMode ? "Exit Batch Mode" : "Batch Operations"}
          </button>

          {batchMode && (
            <>
              <button className="btn secondary" onClick={handleSelectAll}>
                {selectedIds.length === sources.length ? "Deselect All" : "Select All"}
              </button>
              <div style={{ flex: 1, textAlign: "center", opacity: 0.7 }}>
                {selectedIds.length} selected
              </div>
              <button
                className="btn secondary"
                onClick={handleBatchOCR}
                disabled={selectedIds.length === 0}
              >
                Run OCR ({selectedIds.length})
              </button>
              <button
                className="btn secondary"
                onClick={handleBatchDelete}
                disabled={selectedIds.length === 0}
              >
                Delete ({selectedIds.length})
              </button>
            </>
          )}
        </div>
      )}

      <div className="grid two">
        {sources.map((source) => (
          <FileCard
            key={source.id}
            source={source}
            onDelete={batchMode ? undefined : handleDelete}
            onRunOCR={batchMode ? undefined : handleOCR}
            busy={busyIds.includes(source.id)}
            selectable={batchMode}
            selected={selectedIds.includes(source.id)}
            onSelect={handleSelect}
          />
        ))}
        {!sources.length && <p>No files uploaded yet.</p>}
      </div>
    </div>
  );
}

