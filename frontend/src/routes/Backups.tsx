import { useEffect, useState } from "react";
import { Backup, listBackups, restoreBackup } from "../lib/api";

export default function BackupsPage() {
  const [backups, setBackups] = useState<Backup[]>([]);
  const [loading, setLoading] = useState(true);
  const [restoring, setRestoring] = useState<string | null>(null);

  useEffect(() => {
    loadBackups();
  }, []);

  const loadBackups = async () => {
    try {
      setLoading(true);
      const data = await listBackups();
      setBackups(data);
    } catch (error) {
      console.error("Failed to load backups:", error);
      alert("Failed to load backups. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async (backup: Backup) => {
    const confirmMsg = backup.is_autosave
      ? `Restore from autosave created at ${new Date(backup.timestamp).toLocaleString()}?\n\nThis will replace all current data. This action cannot be undone.`
      : `Restore from "${backup.filename}"?\n\nThis will replace all current data. This action cannot be undone.`;

    if (!window.confirm(confirmMsg)) return;

    try {
      setRestoring(backup.filename);
      await restoreBackup(backup.filename);
      alert("Backup restored successfully! The page will reload.");
      window.location.reload();
    } catch (error) {
      console.error("Failed to restore backup:", error);
      alert("Failed to restore backup. Please try again.");
    } finally {
      setRestoring(null);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="grid" style={{ gap: "1.5rem" }}>
        <div className="card">
          <h1>Backups</h1>
          <p>Loading backups...</p>
        </div>
      </div>
    );
  }

  const autosaves = backups.filter(b => b.is_autosave);
  const manualSaves = backups.filter(b => !b.is_autosave);

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <h1>Project Backups</h1>
        <p>
          Restore your project from a previous backup. The application automatically saves your work every 5 minutes,
          keeping the last 5 autosaves. You can also create manual saves for important milestones.
        </p>
        <div style={{ marginTop: "1rem", padding: "0.75rem", background: "rgba(234, 179, 8, 0.1)", border: "1px solid rgba(234, 179, 8, 0.3)", borderRadius: "6px" }}>
          <strong>⚠️ Warning:</strong> Restoring a backup will replace all current data. Make sure to save your current work first if needed.
        </div>
      </div>

      {autosaves.length > 0 && (
        <div className="card">
          <h2>Automatic Backups (Last 5)</h2>
          <p style={{ fontSize: "0.9rem", opacity: 0.8, marginBottom: "1rem" }}>
            Created automatically every 5 minutes
          </p>
          <div className="grid" style={{ gap: "0.75rem" }}>
            {autosaves.map((backup) => (
              <div
                key={backup.filename}
                className="card"
                style={{ background: "rgba(0, 0, 0, 0.25)" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                      <span className="badge" style={{ background: "rgba(34, 197, 94, 0.2)", color: "#22c55e" }}>
                        Auto-save
                      </span>
                      <span style={{ fontSize: "0.85rem", opacity: 0.8 }}>
                        {formatFileSize(backup.size_bytes)}
                      </span>
                    </div>
                    <div style={{ fontSize: "0.9rem" }}>
                      <strong>{formatTimestamp(backup.timestamp)}</strong>
                    </div>
                    <div style={{ fontSize: "0.8rem", opacity: 0.7, marginTop: "0.25rem" }}>
                      {new Date(backup.timestamp).toLocaleString()}
                    </div>
                  </div>
                  <button
                    className="btn secondary"
                    onClick={() => handleRestore(backup)}
                    disabled={restoring === backup.filename}
                  >
                    {restoring === backup.filename ? "Restoring..." : "Restore"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {manualSaves.length > 0 && (
        <div className="card">
          <h2>Manual Saves</h2>
          <p style={{ fontSize: "0.9rem", opacity: 0.8, marginBottom: "1rem" }}>
            Created manually from the Export page
          </p>
          <div className="grid" style={{ gap: "0.75rem" }}>
            {manualSaves.map((backup) => (
              <div
                key={backup.filename}
                className="card"
                style={{ background: "rgba(0, 0, 0, 0.25)" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                      <span className="badge" style={{ background: "rgba(79, 156, 255, 0.2)", color: "#4f9cff" }}>
                        Manual
                      </span>
                      <span style={{ fontSize: "0.85rem", opacity: 0.8 }}>
                        {formatFileSize(backup.size_bytes)}
                      </span>
                    </div>
                    <div style={{ fontSize: "0.9rem" }}>
                      <strong>{backup.filename}</strong>
                    </div>
                    <div style={{ fontSize: "0.8rem", opacity: 0.7, marginTop: "0.25rem" }}>
                      {new Date(backup.timestamp).toLocaleString()}
                    </div>
                  </div>
                  <button
                    className="btn secondary"
                    onClick={() => handleRestore(backup)}
                    disabled={restoring === backup.filename}
                  >
                    {restoring === backup.filename ? "Restoring..." : "Restore"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {backups.length === 0 && (
        <div className="card">
          <p style={{ textAlign: "center", opacity: 0.6 }}>
            No backups available yet. Backups are created automatically every 5 minutes when you're working on your project.
          </p>
        </div>
      )}
    </div>
  );
}
