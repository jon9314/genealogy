import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { openProject, saveProject, deleteAllData, getDataStats } from "../lib/api";
import { useUndoRedo } from "../hooks/useUndoRedo";
import UndoHistoryViewer from "./UndoHistoryViewer";

export default function Toolbar() {
  const { history } = useUndoRedo();
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

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

  const handleDeleteAll = async () => {
    try {
      // First, get current stats
      const stats = await getDataStats();

      const message = `⚠️ WARNING: This will delete ALL parsed data!\n\n` +
        `Current data:\n` +
        `• ${stats.persons} persons\n` +
        `• ${stats.families} families\n` +
        `• ${stats.children} child relationships\n\n` +
        `OCR text and source files will be preserved.\n\n` +
        `Are you absolutely sure you want to delete all this data?`;

      if (!window.confirm(message)) return;

      // Double confirmation
      if (!window.confirm("This cannot be undone. Delete all parsed data?")) return;

      setDeleting(true);

      const result = await deleteAllData({
        confirm: true,
        delete_sources: false,
        delete_ocr: false
      });

      window.alert(`✓ Successfully deleted:\n` +
        `• ${result.stats.persons_deleted} persons\n` +
        `• ${result.stats.families_deleted} families\n` +
        `• ${result.stats.children_deleted} child relationships`
      );

      // Redirect to home and reload
      navigate("/");
      window.location.reload();

    } catch (err) {
      console.error(err);
      window.alert("Failed to delete data. Check console for details.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
      <div>
        <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{titleForRoute(location.pathname)}</div>
        <div style={{ opacity: 0.7, fontSize: "0.9rem" }}>Undo stack: {history.length}</div>
      </div>
      <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
        <UndoHistoryViewer />
        <button
          className="btn"
          onClick={handleDeleteAll}
          disabled={deleting}
          style={{
            backgroundColor: "#dc2626",
            borderColor: "#dc2626",
            color: "white"
          }}
          title="Delete all parsed persons, families, and relationships (OCR and sources are kept)"
        >
          {deleting ? "Deleting..." : "🗑️ Delete All Data"}
        </button>
        <button className="btn secondary" onClick={handleOpen} disabled={loading}>
          {loading ? "Opening..." : "Open"}
        </button>
        <button className="btn" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </button>
        <button
          className="btn secondary"
          onClick={() => navigate("/settings")}
          title="Application settings"
        >
          ⚙️ Settings
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
