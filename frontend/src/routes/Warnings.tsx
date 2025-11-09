import { useEffect, useState } from "react";

import { getValidationWarnings } from "../lib/api";
import type { ValidationWarning } from "../lib/types";

export default function WarningsPage() {
  const [warnings, setWarnings] = useState<ValidationWarning[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "error" | "warning" | "info">("all");

  useEffect(() => {
    loadWarnings();
  }, []);

  const loadWarnings = async () => {
    setLoading(true);
    try {
      const data = await getValidationWarnings();
      setWarnings(data);
    } catch (error) {
      console.error("Failed to load validation warnings:", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredWarnings = warnings.filter((w) => filter === "all" || w.severity === filter);

  const errorCount = warnings.filter((w) => w.severity === "error").length;
  const warningCount = warnings.filter((w) => w.severity === "warning").length;
  const infoCount = warnings.filter((w) => w.severity === "info").length;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "error":
        return "#ef4444";
      case "warning":
        return "#f59e0b";
      case "info":
        return "#3b82f6";
      default:
        return "#6b7280";
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "error":
        return "⛔";
      case "warning":
        return "⚠️";
      case "info":
        return "ℹ️";
      default:
        return "•";
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case "dates":
        return "Date Issues";
      case "age_gaps":
        return "Age Gaps";
      case "duplicates":
        return "Duplicate Names";
      default:
        return category;
    }
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <h2>Data Validation Warnings</h2>
        <p>
          Automatically detected data quality issues including impossible dates,
          suspicious age gaps, and duplicate names within families.
        </p>
      </div>

      {loading ? (
        <div className="card">Loading validation warnings...</div>
      ) : (
        <>
          {/* Summary & Filters */}
          <div className="card" style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ flex: 1 }}>
              <strong>Total: {warnings.length}</strong>
            </div>
            <button
              className={`btn ${filter === "all" ? "" : "secondary"}`}
              onClick={() => setFilter("all")}
              style={{ minWidth: "100px" }}
            >
              All ({warnings.length})
            </button>
            <button
              className={`btn ${filter === "error" ? "" : "secondary"}`}
              onClick={() => setFilter("error")}
              style={{ minWidth: "100px", color: filter === "error" ? "#fff" : "#ef4444" }}
            >
              ⛔ Errors ({errorCount})
            </button>
            <button
              className={`btn ${filter === "warning" ? "" : "secondary"}`}
              onClick={() => setFilter("warning")}
              style={{ minWidth: "120px", color: filter === "warning" ? "#fff" : "#f59e0b" }}
            >
              ⚠️ Warnings ({warningCount})
            </button>
            <button
              className={`btn ${filter === "info" ? "" : "secondary"}`}
              onClick={() => setFilter("info")}
              style={{ minWidth: "100px", color: filter === "info" ? "#fff" : "#3b82f6" }}
            >
              ℹ️ Info ({infoCount})
            </button>
            <button className="btn secondary" onClick={loadWarnings}>
              Refresh
            </button>
          </div>

          {/* Warnings List */}
          {filteredWarnings.length === 0 ? (
            <div className="card" style={{ textAlign: "center", padding: "2rem" }}>
              {filter === "all"
                ? "✅ No validation warnings found! Your data looks good."
                : `No ${filter} level warnings.`}
            </div>
          ) : (
            <div className="grid" style={{ gap: "0.75rem" }}>
              {filteredWarnings.map((warning, idx) => (
                <div
                  key={idx}
                  className="card"
                  style={{
                    borderLeft: `4px solid ${getSeverityColor(warning.severity)}`,
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.5rem",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    <span style={{ fontSize: "1.5rem" }}>{getSeverityIcon(warning.severity)}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>
                        {getCategoryLabel(warning.category)}
                      </div>
                      <div style={{ fontSize: "0.9rem" }}>{warning.message}</div>
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", fontSize: "0.85rem", opacity: 0.8 }}>
                    {warning.person_ids.map((id) => (
                      <span key={id} className="badge">
                        Person ID: {id}
                      </span>
                    ))}
                    {warning.family_id && (
                      <span className="badge" style={{ backgroundColor: "rgba(245, 158, 11, 0.15)", color: "#f59e0b" }}>
                        Family ID: {warning.family_id}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
