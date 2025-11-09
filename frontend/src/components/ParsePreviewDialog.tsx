interface ParsePreviewData {
  people: number;
  families: number;
  children: number;
  flagged_lines: string[];
  sample_people: Array<{
    name: string;
    gen: number;
    birth: string | null;
    death: string | null;
    surname: string | null;
  }>;
  sample_families: Array<{
    id: number;
    husband_id: number | null;
    wife_id: number | null;
  }>;
}

interface ParsePreviewDialogProps {
  preview: ParsePreviewData;
  sourceName: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export default function ParsePreviewDialog({
  preview,
  sourceName,
  onConfirm,
  onCancel,
  loading = false,
}: ParsePreviewDialogProps) {
  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onCancel}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.7)",
          zIndex: 999,
        }}
      />

      {/* Dialog */}
      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          backgroundColor: "rgba(0, 0, 0, 0.95)",
          border: "1px solid rgba(255, 255, 255, 0.2)",
          borderRadius: "10px",
          padding: "2rem",
          zIndex: 1000,
          minWidth: "600px",
          maxWidth: "90vw",
          maxHeight: "90vh",
          overflow: "auto",
        }}
      >
        <div style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ marginBottom: "0.5rem" }}>Parse Preview: {sourceName}</h2>
          <p style={{ opacity: 0.7, fontSize: "0.9rem" }}>
            Review what will be parsed before committing to the database
          </p>
        </div>

        {/* Statistics */}
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <h3 style={{ marginBottom: "1rem" }}>Summary</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "1rem" }}>
            <div>
              <div style={{ fontSize: "2rem", fontWeight: 700, color: "#4f9cff" }}>
                {preview.people}
              </div>
              <div style={{ opacity: 0.7, fontSize: "0.85rem" }}>
                {preview.people === 1 ? "Person" : "People"}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "2rem", fontWeight: 700, color: "#22c55e" }}>
                {preview.families}
              </div>
              <div style={{ opacity: 0.7, fontSize: "0.85rem" }}>
                {preview.families === 1 ? "Family" : "Families"}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "2rem", fontWeight: 700, color: "#f59e0b" }}>
                {preview.children}
              </div>
              <div style={{ opacity: 0.7, fontSize: "0.85rem" }}>
                {preview.children === 1 ? "Child Link" : "Child Links"}
              </div>
            </div>
            {preview.flagged_lines.length > 0 && (
              <div>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "#ef4444" }}>
                  {preview.flagged_lines.length}
                </div>
                <div style={{ opacity: 0.7, fontSize: "0.85rem" }}>Unparsed Lines</div>
              </div>
            )}
          </div>
        </div>

        {/* Sample People */}
        {preview.sample_people.length > 0 && (
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ marginBottom: "1rem" }}>Sample People (first 10)</h3>
            <div style={{ display: "grid", gap: "0.5rem" }}>
              {preview.sample_people.map((person, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: "0.75rem",
                    backgroundColor: "rgba(255, 255, 255, 0.05)",
                    borderRadius: "5px",
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "1rem",
                  }}
                >
                  <div>
                    <span style={{ fontWeight: 600 }}>{person.name}</span>
                    {person.surname && (
                      <span style={{ marginLeft: "0.5rem", opacity: 0.7 }}>({person.surname})</span>
                    )}
                  </div>
                  <div style={{ fontSize: "0.85rem", opacity: 0.7 }}>
                    Gen {person.gen} • {person.birth || "?"} - {person.death || "?"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Flagged Lines */}
        {preview.flagged_lines.length > 0 && (
          <div className="card" style={{ marginBottom: "1.5rem", borderLeft: "4px solid #ef4444" }}>
            <h3 style={{ marginBottom: "1rem", color: "#ef4444" }}>
              ⚠️ Unparsed Lines ({preview.flagged_lines.length})
            </h3>
            <p style={{ fontSize: "0.85rem", opacity: 0.7, marginBottom: "0.75rem" }}>
              These lines could not be parsed and will be skipped:
            </p>
            <div
              style={{
                maxHeight: "200px",
                overflow: "auto",
                backgroundColor: "rgba(0, 0, 0, 0.3)",
                padding: "0.75rem",
                borderRadius: "5px",
                fontFamily: "monospace",
                fontSize: "0.85rem",
              }}
            >
              {preview.flagged_lines.map((line, idx) => (
                <div key={idx} style={{ marginBottom: "0.25rem" }}>
                  {line}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: "1rem", justifyContent: "flex-end" }}>
          <button className="btn secondary" onClick={onCancel} disabled={loading}>
            Cancel
          </button>
          <button className="btn" onClick={onConfirm} disabled={loading}>
            {loading ? "Parsing..." : "Confirm & Parse"}
          </button>
        </div>
      </div>
    </>
  );
}
