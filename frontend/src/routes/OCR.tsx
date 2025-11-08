import { useEffect, useState } from "react";

import FileCard from "../components/FileCard";
import { getOCRStatus, listSources, runOCR } from "../lib/api";
import type { Source } from "../lib/types";

export default function OCRPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [status, setStatus] = useState<Record<number, { pages: number; ocr_done: boolean }>>({});
  const [busy, setBusy] = useState<number[]>([]);

  useEffect(() => {
    refresh();
  }, []);

  const refresh = async () => {
    const data = await listSources();
    setSources(data);
    const next: Record<number, { pages: number; ocr_done: boolean }> = {};
    for (const item of data) {
      if (!item.id) continue;
      next[item.id] = await getOCRStatus(item.id).catch(() => ({ pages: 0, ocr_done: false }));
    }
    setStatus(next);
  };

  const handleOCR = async (id: number) => {
    setBusy((prev) => [...prev, id]);
    try {
      await runOCR(id);
      await refresh();
    } finally {
      setBusy((prev) => prev.filter((value) => value !== id));
    }
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <h2>OCR pipeline</h2>
        <p>Runs OCRmyPDF with deskew, rotate, and optimize 3. Results are stored in ./data/ocr.</p>
      </div>
      <div className="grid two">
        {sources.map((source) => (
          <div key={source.id} className="grid" style={{ gap: "0.75rem" }}>
            <FileCard source={source} onRunOCR={handleOCR} busy={busy.includes(source.id)} />
            <div className="card" style={{ fontSize: "0.9rem", opacity: 0.85 }}>
              <div>Pages: {status[source.id]?.pages ?? source.pages}</div>
              {busy.includes(source.id) ? (
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
                      animation: "progress 1.5s ease-in-out infinite",
                      width: "40%",
                      position: "absolute"
                    }} />
                  </div>
                  <div style={{ whiteSpace: "nowrap", fontWeight: 500 }}>Processing OCR...</div>
                </div>
              ) : (
                <div style={{ color: status[source.id]?.ocr_done ? "#22c55e" : "#6b7280" }}>
                  OCR status: {status[source.id]?.ocr_done ? "✓ Complete" : "Pending"}
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

