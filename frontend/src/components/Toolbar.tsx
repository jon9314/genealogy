import { useState } from "react";
import { useLocation } from "react-router-dom";

import { openProject, saveProject } from "../lib/api";
import { useUndoRedo } from "../hooks/useUndoRedo";

export default function Toolbar() {
  const { canUndo, canRedo, undo, redo, history } = useUndoRedo();
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const location = useLocation();

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveProject();
    } finally {
      setSaving(false);
    }
  };

  const handleOpen = async () => {
    const filename = window.prompt("Enter project filename to open (e.g. project-20240101.json)");
    if (!filename) return;
    setLoading(true);
    try {
      await openProject(filename);
      window.location.reload();
    } catch (err) {
      console.error(err);
      window.alert("Failed to open project");
    } finally {
      setLoading(false);
    }
  };

  return (
    <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
      <div>
        <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{titleForRoute(location.pathname)}</div>
        <div style={{ opacity: 0.7, fontSize: "0.9rem" }}>Undo stack: {history.length}</div>
      </div>
      <div style={{ display: "flex", gap: "0.75rem" }}>
        <button className="btn secondary" disabled={!canUndo} onClick={() => void undo()}>
          Undo
        </button>
        <button className="btn secondary" disabled={!canRedo} onClick={() => void redo()}>
          Redo
        </button>
        <button className="btn secondary" onClick={handleOpen} disabled={loading}>
          {loading ? "Opening..." : "Open"}
        </button>
        <button className="btn" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
    </header>
  );
}

function titleForRoute(path: string): string {
  if (path === "/") return "Overview";
  return path
    .replace(/^\//, "")
    .split("/")[0]
    .replace(/-/g, " ")
    .toLowerCase()
    .replace(/(^|\s)\w/g, (s) => s.toUpperCase());
}
