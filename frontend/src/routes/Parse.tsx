import { useEffect, useState } from "react";

import ParsePreviewDialog from "../components/ParsePreviewDialog";
import { listSources, parseSource, parseSourcePreview, getParseProgress } from "../lib/api";
import type { Source, ParsePreview } from "../lib/types";

interface ParseResult {
  people: number;
  families: number;
  flagged_lines: string[];
}

export default function ParsePage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [results, setResults] = useState<Record<number, ParseResult>>({});
  const [jobIds, setJobIds] = useState<Record<number, string>>({});
  const [progress, setProgress] = useState<Record<string, { current: number; total: number }>>({});
  const [preview, setPreview] = useState<{ sourceId: number; data: ParsePreview; sourceName: string } | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  useEffect(() => {
    listSources().then(setSources);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      Object.entries(jobIds).forEach(async ([sourceId, jobId]) => {
        const status = await getParseProgress(jobId);
        if (status.progress) {
          setProgress((prev) => ({ ...prev, [jobId]: status.progress }));
        }
        if (status.status === "completed" || status.status === "failed") {
          setJobIds((prev) => {
            const next = { ...prev };
            delete next[Number(sourceId)];
            return next;
          });
          if (status.status === "completed") {
            setResults((prev) => ({ ...prev, [Number(sourceId)]: status.stats }));
          }
        }
      });
    }, 2000);
    return () => clearInterval(interval);
  }, [jobIds]);

  const handleShowPreview = async (id: number, sourceName: string) => {
    setLoadingPreview(true);
    try {
      const data = await parseSourcePreview(id);
      setPreview({ sourceId: id, data, sourceName });
    } catch (error) {
      console.error(error);
      window.alert("Preview failed; check backend logs.");
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleConfirmParse = async () => {
    if (!preview) return;

    const sourceId = preview.sourceId;
    setPreview(null);

    try {
      const { job_id } = await parseSource(sourceId);
      setJobIds((prev) => ({ ...prev, [sourceId]: job_id }));
    } catch (error) {
      console.error(error);
      window.alert("Parse failed; check backend logs.");
    }
  };

  const handleCancelPreview = () => {
    setPreview(null);
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <h2>Parse OCR text into structured families</h2>
        <p>Preserves chart IDs, attaches spouses, and links generations using stack logic.</p>
      </div>
      <div className="grid two">
        {sources.map((source) => {
          const result = results[source.id];
          const jobId = Object.entries(jobIds).find(([sourceId]) => Number(sourceId) === source.id)?.[1];
          const jobProgress = jobId ? progress[jobId] : null;
          const isRunning = !!jobId;

          return (
            <div key={source.id} className="card" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{source.name}</div>
                  <div className="badge">ID {source.id}</div>
                </div>
                <button
                  className="btn"
                  onClick={() => handleShowPreview(source.id, source.name)}
                  disabled={isRunning || loadingPreview}
                >
                  {isRunning
                    ? `Parsing... ${jobProgress ? `${Math.round((jobProgress.current / jobProgress.total) * 100)}%` : ""}`
                    : loadingPreview
                    ? "Loading preview..."
                    : "Preview & Parse"}
                </button>
              </div>
              {result && (
                <div style={{ fontSize: "0.9rem", opacity: 0.85 }}>
                  <div style={{ fontWeight: 600, color: "#22c55e", marginBottom: "0.5rem" }}>
                    ✓ Found {result.people} {result.people === 1 ? "person" : "people"}, {result.families} {result.families === 1 ? "family" : "families"}
                    {result.flagged_lines.length > 0 && `, ${result.flagged_lines.length} unparsed ${result.flagged_lines.length === 1 ? "line" : "lines"}`}
                  </div>
                  {result.flagged_lines.length > 0 ? (
                    <details>
                      <summary style={{ cursor: "pointer", color: "#f59e0b" }}>⚠ View unparsed lines ({result.flagged_lines.length})</summary>
                      <ul style={{ marginTop: "0.5rem", paddingLeft: "1.25rem" }}>
                        {result.flagged_lines.map((item, idx) => (
                          <li key={idx} style={{ fontFamily: "monospace", fontSize: "0.85rem" }}>{item}</li>
                        ))}
                      </ul>
                    </details>
                  ) : (
                    <div style={{ color: "#22c55e" }}>All lines parsed successfully.</div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {!sources.length && <p>No sources to parse yet.</p>}
      </div>

      {/* Preview Dialog */}
      {preview && (
        <ParsePreviewDialog
          preview={preview.data}
          sourceName={preview.sourceName}
          onConfirm={handleConfirmParse}
          onCancel={handleCancelPreview}
          loading={!!jobIds[preview.sourceId]}
        />
      )}
    </div>
  );
}
