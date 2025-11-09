import { useState } from "react";
import { useUndoRedo } from "../hooks/useUndoRedo";

export default function UndoHistoryViewer() {
  const { history, currentPosition, canUndo, canRedo, undo, redo, saveCheckpoint } = useUndoRedo();
  const [showHistory, setShowHistory] = useState(false);
  const [checkpointLabel, setCheckpointLabel] = useState("");

  const handleSaveCheckpoint = () => {
    if (!checkpointLabel.trim()) return;
    saveCheckpoint(checkpointLabel);
    setCheckpointLabel("");
  };

  return (
    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
      <button className="btn secondary" onClick={undo} disabled={!canUndo} title="Undo">
        ↶ Undo
      </button>
      <button className="btn secondary" onClick={redo} disabled={!canRedo} title="Redo">
        ↷ Redo
      </button>
      <button
        className="btn secondary"
        onClick={() => setShowHistory(!showHistory)}
        title="Show undo/redo history"
      >
        📜 History ({history.length})
      </button>

      {showHistory && (
        <div
          style={{
            position: "fixed",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            backgroundColor: "rgba(0, 0, 0, 0.95)",
            border: "1px solid rgba(255, 255, 255, 0.2)",
            borderRadius: "10px",
            padding: "1.5rem",
            zIndex: 1000,
            minWidth: "400px",
            maxWidth: "600px",
            maxHeight: "80vh",
            overflow: "auto",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h3 style={{ margin: 0 }}>Undo/Redo History</h3>
            <button className="btn secondary" onClick={() => setShowHistory(false)}>
              ✕ Close
            </button>
          </div>

          <div style={{ marginBottom: "1.5rem" }}>
            <p style={{ fontSize: "0.85rem", opacity: 0.7, marginBottom: "0.75rem" }}>
              Save a checkpoint to mark important milestones:
            </p>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <input
                type="text"
                placeholder="Checkpoint name (e.g., 'After parsing')"
                value={checkpointLabel}
                onChange={(e) => setCheckpointLabel(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSaveCheckpoint()}
                style={{
                  flex: 1,
                  padding: "0.5rem",
                  backgroundColor: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  borderRadius: "5px",
                  color: "white",
                }}
              />
              <button className="btn" onClick={handleSaveCheckpoint} disabled={!checkpointLabel.trim()}>
                Save Checkpoint
              </button>
            </div>
          </div>

          {history.length === 0 ? (
            <p style={{ textAlign: "center", opacity: 0.5 }}>No actions yet</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {history.map((action, index) => {
                const isCurrent = index === currentPosition - 1;
                const isCheckpoint = action.isCheckpoint;

                return (
                  <div
                    key={index}
                    style={{
                      padding: "0.75rem",
                      backgroundColor: isCurrent
                        ? "rgba(79, 156, 255, 0.15)"
                        : isCheckpoint
                        ? "rgba(251, 191, 36, 0.1)"
                        : "rgba(255, 255, 255, 0.05)",
                      border: isCurrent
                        ? "1px solid rgba(79, 156, 255, 0.6)"
                        : isCheckpoint
                        ? "1px solid rgba(251, 191, 36, 0.3)"
                        : "1px solid rgba(255, 255, 255, 0.05)",
                      borderRadius: "5px",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.75rem",
                      fontWeight: isCheckpoint ? 600 : 400,
                    }}
                  >
                    <div style={{ opacity: 0.5, fontSize: "0.75rem", minWidth: "30px" }}>
                      #{index + 1}
                    </div>
                    <div style={{ flex: 1 }}>{action.label}</div>
                    {isCurrent && (
                      <span style={{ fontSize: "0.75rem", color: "#4f9cff" }}>← Current</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <div style={{ marginTop: "1rem", fontSize: "0.85rem", opacity: 0.7 }}>
            <p style={{ marginBottom: "0.5rem" }}>
              <strong>Undoable actions:</strong>
            </p>
            <ul style={{ paddingLeft: "1.5rem", margin: 0 }}>
              <li>Person edits (name, dates, notes, etc.)</li>
              <li>Family relationship changes</li>
              <li>Person deletion</li>
              <li>Reparenting operations</li>
            </ul>
          </div>
        </div>
      )}

      {/* Backdrop */}
      {showHistory && (
        <div
          onClick={() => setShowHistory(false)}
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            zIndex: 999,
          }}
        />
      )}
    </div>
  );
}
