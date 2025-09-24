import type { Source } from "../lib/types";

interface Props {
  source: Source;
  onDelete?: (id: number) => void;
  onRunOCR?: (id: number) => void;
  onParse?: (id: number) => void;
  busy?: boolean;
}

export default function FileCard({ source, onDelete, onRunOCR, onParse, busy = false }: Props) {
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontWeight: 600 }}>{source.name}</div>
          <div className="badge">ID {source.id}</div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {onRunOCR && (
            <button className="btn secondary" onClick={() => onRunOCR(source.id)} disabled={busy}>
              {busy ? "Processing..." : "Run OCR"}
            </button>
          )}
          {onParse && (
            <button className="btn secondary" onClick={() => onParse(source.id)} disabled={busy}>
              Parse
            </button>
          )}
          {onDelete && (
            <button className="btn secondary" onClick={() => onDelete(source.id)} disabled={busy}>
              Delete
            </button>
          )}
        </div>
      </div>
      <div style={{ display: "flex", gap: "1.5rem", fontSize: "0.85rem", opacity: 0.8 }}>
        <span>Pages: {source.pages}</span>
        <span>OCR: {source.ocr_done ? "Complete" : "Pending"}</span>
      </div>
    </div>
  );
}
