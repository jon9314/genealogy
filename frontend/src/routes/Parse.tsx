import { useEffect, useState } from "react";

import { listSources, parseSource } from "../lib/api";
import type { Source } from "../lib/types";

interface ParseResult {
  people: number;
  families: number;
  flagged_lines: string[];
}

export default function ParsePage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [results, setResults] = useState<Record<number, ParseResult>>({});
  const [runningId, setRunningId] = useState<number | null>(null);

  useEffect(() => {
    listSources().then(setSources);
  }, []);

  const handleParse = async (id: number) => {
    setRunningId(id);
    try {
      const data = await parseSource(id);
      setResults((prev) => ({ ...prev, [id]: data }));
    } catch (error) {
      console.error(error);
      window.alert("Parse failed; check backend logs.");
    } finally {
      setRunningId(null);
    }
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
          return (
            <div key={source.id} className="card" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{source.name}</div>
                  <div className="badge">ID {source.id}</div>
                </div>
                <button className="btn" onClick={() => handleParse(source.id)} disabled={runningId === source.id}>
                  {runningId === source.id ? "Parsing..." : "Run parser"}
                </button>
              </div>
              {result && (
                <div style={{ fontSize: "0.9rem", opacity: 0.85 }}>
                  <div>People: {result.people}</div>
                  <div>Families: {result.families}</div>
                  {result.flagged_lines.length > 0 ? (
                    <details>
                      <summary>Flagged lines ({result.flagged_lines.length})</summary>
                      <ul>
                        {result.flagged_lines.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </details>
                  ) : (
                    <div>No flagged lines.</div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {!sources.length && <p>No sources to parse yet.</p>}
      </div>
    </div>
  );
}
