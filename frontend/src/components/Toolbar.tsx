import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { openProject, saveProject, deleteAllData, getDataStats, type DataStats } from "../lib/api";
import { useUndoRedo } from "../hooks/useUndoRedo";
import UndoHistoryViewer from "./UndoHistoryViewer";

export default function Toolbar() {
  const { history } = useUndoRedo();
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteOptions, setDeleteOptions] = useState({
    deleteOcr: false,
    deleteSources: false
  });
  const [stats, setStats] = useState<DataStats | null>(null);
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
      // Get current stats and show dialog
      const currentStats = await getDataStats();
      setStats(currentStats);
      setShowDeleteDialog(true);
    } catch (err) {
      console.error(err);
      window.alert("Failed to load stats. Check console for details.");
    }
  };

  const confirmDelete = async () => {
    try {
      setDeleting(true);
      setShowDeleteDialog(false);

      const result = await deleteAllData({
        confirm: true,
        delete_sources: deleteOptions.deleteSources,
        delete_ocr: deleteOptions.deleteOcr
      });

      let message = `✓ Successfully deleted:\n` +
        `• ${result.stats.persons_deleted} persons\n` +
        `• ${result.stats.families_deleted} families\n` +
        `• ${result.stats.children_deleted} child relationships`;

      if (deleteOptions.deleteOcr && result.stats.ocr_pages_deleted) {
        message += `\n• ${result.stats.ocr_pages_deleted} OCR pages`;
      }
      if (deleteOptions.deleteSources && result.stats.sources_deleted) {
        message += `\n• ${result.stats.sources_deleted} source files`;
      }

      window.alert(message);

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
    <>
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
            title="Delete all parsed persons, families, and relationships"
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

      {/* Delete Confirmation Dialog */}
      {showDeleteDialog && stats && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: "white",
            borderRadius: "8px",
            padding: "2rem",
            maxWidth: "500px",
            width: "90%",
            boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)"
          }}>
            <h2 style={{ marginTop: 0, marginBottom: "1rem", color: "#dc2626" }}>
              ⚠️ Delete All Data
            </h2>

            <div style={{ marginBottom: "1.5rem", lineHeight: "1.6" }}>
              <p style={{ marginBottom: "1rem" }}>
                <strong>Current data that will be deleted:</strong>
              </p>
              <ul style={{ marginLeft: "1.5rem", marginBottom: "1rem" }}>
                <li>{stats.persons} persons</li>
                <li>{stats.families} families</li>
                <li>{stats.children} child relationships</li>
              </ul>

              <div style={{
                backgroundColor: "#fef3c7",
                border: "1px solid #fbbf24",
                borderRadius: "6px",
                padding: "1rem",
                marginBottom: "1rem"
              }}>
                <p style={{ margin: 0, fontSize: "0.9rem" }}>
                  <strong>Additional options:</strong>
                </p>
              </div>

              <label style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                marginBottom: "0.75rem",
                cursor: "pointer"
              }}>
                <input
                  type="checkbox"
                  checked={deleteOptions.deleteOcr}
                  onChange={(e) => setDeleteOptions({ ...deleteOptions, deleteOcr: e.target.checked })}
                  style={{ width: "18px", height: "18px", cursor: "pointer" }}
                />
                <span>Delete OCR text ({stats.ocr_pages} pages)</span>
              </label>

              <label style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                marginBottom: "1rem",
                cursor: "pointer"
              }}>
                <input
                  type="checkbox"
                  checked={deleteOptions.deleteSources}
                  onChange={(e) => setDeleteOptions({ ...deleteOptions, deleteSources: e.target.checked })}
                  style={{ width: "18px", height: "18px", cursor: "pointer" }}
                />
                <span>Delete source files ({stats.sources} files)</span>
              </label>

              <p style={{
                fontSize: "0.85rem",
                color: "#dc2626",
                fontWeight: 600,
                marginTop: "1rem"
              }}>
                This action cannot be undone!
              </p>
            </div>

            <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
              <button
                className="btn secondary"
                onClick={() => {
                  setShowDeleteDialog(false);
                  setDeleteOptions({ deleteOcr: false, deleteSources: false });
                }}
              >
                Cancel
              </button>
              <button
                className="btn"
                onClick={confirmDelete}
                style={{
                  backgroundColor: "#dc2626",
                  borderColor: "#dc2626",
                  color: "white"
                }}
              >
                Delete All Data
              </button>
            </div>
          </div>
        </div>
      )}
    </>
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
