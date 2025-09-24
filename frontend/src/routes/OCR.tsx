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
              <div>OCR status: {status[source.id]?.ocr_done ? "Complete" : "Pending"}</div>
            </div>
          </div>
        ))}
        {!sources.length && <p>No sources yet.</p>}
      </div>
    </div>
  );
}

