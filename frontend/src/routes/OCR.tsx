import { useEffect, useState } from "react";

import FileCard from "../components/FileCard";
import { getOCRStatus, listSources, runOCR, getOCRProgress } from "../lib/api";
import type { Source } from "../lib/types";

interface OCRStatus {
  pages: number;
  ocr_done: boolean;
  progress?: {
    percent: number;
    current_page: number;
    total_pages: number;
  };
  error?: {
    message: string;
    suggestion: string;
  };
}

export default function OCRPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [status, setStatus] = useState<Record<number, OCRStatus>>({});
  const [busy, setBusy] = useState<number[]>([]);
  const [jobIds, setJobIds] = useState<Record<number, string>>({});
  const [includeConfidence, setIncludeConfidence] = useState(false);

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      Object.entries(jobIds).forEach(async ([sourceId, jobId]) => {
        const status = await getOCRProgress(jobId);
        setStatus((prev) => ({ ...prev, [Number(sourceId)]: { ...prev[Number(sourceId)], ...status } }));
        if (status.status === "completed" || status.status === "failed") {
          setJobIds((prev) => {
            const next = { ...prev };
            delete next[Number(sourceId)];
            return next;
          });
          if (status.status === "completed") {
            await getOCRStatus(Number(sourceId), jobId, includeConfidence);
            await refresh();
          }
        }
      });
    }, 2000);
    return () => clearInterval(interval);
  }, [jobIds, includeConfidence]);

  const refresh = async () => {
    const data = await listSources();
    setSources(data);
    const next: Record<number, OCRStatus> = {};
    for (const item of data) {
      if (!item.id) continue;
      next[item.id] = await getOCRStatus(item.id).catch(() => ({ pages: 0, ocr_done: false }));
    }
    setStatus(next);
  };

  const handleOCR = async (id: number) => {
    setBusy((prev) => [...prev, id]);
    try {
      const { job_id } = await runOCR(id);
      setJobIds((prev) => ({ ...prev, [id]: job_id }));
    } finally {
      // Don't remove from busy here, let the polling handle it
    }
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <h2>OCR pipeline</h2>
        <p>Runs OCRmyPDF with deskew, rotate, and optimize 3. Results are stored in ./data/ocr.</p>
        <div style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <input
            type="checkbox"
            id="include-confidence"
            checked={includeConfidence}
            onChange={(e) => setIncludeConfidence(e.target.checked)}
          />
          <label htmlFor="include-confidence" style={{ cursor: "pointer" }}>
            Include confidence scores (slower, uses Tesseract for detailed analysis)
          </label>
        </div>
      </div>
      <div className="grid two">
        {sources.map((source) => (
          <div key={source.id} className="grid" style={{ gap: "0.75rem" }}>
            <FileCard source={source} onRunOCR={handleOCR} busy={busy.includes(source.id)} />
            <div className="card" style={{ fontSize: "0.9rem", opacity: 0.85 }}>
              <div>Pages: {status[source.id]?.pages ?? source.pages}</div>
              {jobIds[source.id] ? (
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#3b82f6" }}>
                  <div style={{
                    width: "100%",
                    height: "4px",
                    backgroundColor: "#e5e7eb",
                    borderRadius: "2px",
                    overflow: "hidden",
                    position: "relative"
                  }}>
                    <div style={{
                      height: "100%",
                      backgroundColor: "#3b82f6",
                      width: `${status[source.id]?.progress?.percent ?? 0}%`,
                      transition: "width 0.5s ease-in-out",
                    }} />
                  </div>
                  <div style={{ whiteSpace: "nowrap", fontWeight: 500 }}>
                    {status[source.id]?.progress
                      ? `Processing: ${status[source.id]?.progress?.current_page}/${status[source.id]?.progress?.total_pages}`
                      : "Starting..."}
                  </div>
                </div>
              ) : (
                <div style={{ color: status[source.id]?.ocr_done ? "#22c55e" : "#6b7280" }}>
                  OCR status: {status[source.id]?.ocr_done ? "✓ Complete" : "Pending"}
                </div>
              )}
              {status[source.id]?.error && (
                <div style={{ color: "red", marginTop: "0.5rem" }}>
                  <strong>Error:</strong> {status[source.id]?.error?.message}
                  {status[source.id]?.error?.suggestion && <p>{status[source.id]?.error?.suggestion}</p>}
                </div>
              )}
            </div>
          </div>
        ))}
        {!sources.length && <p>No sources yet.</p>}
      </div>
    </div>
  );
}
