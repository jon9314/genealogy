import { useState } from "react";
import axios from "axios";
import client from "../lib/api";

interface ImportData {
  persons: Array<{ id: number; action: string; name?: string }>;
  families: Array<{ id: number; action: string }>;
  children: Array<{ family_id: number; person_id: number }>;
  source_id: number;
  errors: string[];
}

interface ImportResults {
  message: string;
  data?: ImportData;
  error?: string;
}

export default function ImportPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importResults, setImportResults] = useState<ImportResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [rolling, setRolling] = useState(false);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setSelectedFile(event.target.files[0]);
      setImportResults(null); // Clear previous results
    } else {
      setSelectedFile(null);
    }
  };

  const handleImport = async () => {
    if (!selectedFile) {
      alert("Please select a GEDCOM file to import.");
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await client.post("/import/gedcom", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      setImportResults(response.data);
    } catch (error: unknown) {
      console.error("Failed to import GEDCOM file:", error);
      const errorMsg = axios.isAxiosError(error) && error.response?.data?.detail
        ? error.response.data.detail
        : "Failed to import GEDCOM file.";
      setImportResults({ message: "", error: errorMsg });
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async () => {
    if (!importResults?.data?.source_id) {
      alert("No import to rollback");
      return;
    }

    if (!confirm("Are you sure you want to undo this import? This will delete all imported records.")) {
      return;
    }

    setRolling(true);
    try {
      const response = await client.delete(`/import/rollback/${importResults.data.source_id}`);
      alert(response.data.message + `\nDeleted ${response.data.deleted.persons} persons and ${response.data.deleted.families} families.`);
      setImportResults(null);
      setSelectedFile(null);
    } catch (error: unknown) {
      console.error("Failed to rollback import:", error);
      const errorMsg = axios.isAxiosError(error) && error.response?.data?.detail
        ? error.response.data.detail
        : "Failed to rollback import.";
      alert(errorMsg);
    } finally {
      setRolling(false);
    }
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <h2>Import GEDCOM</h2>
        <p>
          Upload a GEDCOM file to import existing family trees into your workbench.
          The imported data will be merged with your current project.
        </p>
        <p style={{ fontSize: "0.9em", color: "#666", marginTop: "0.5rem" }}>
          <strong>How merging works:</strong> People with matching names and birth dates
          will be updated with missing information. New people and families will be created
          for records that don't exist yet.
        </p>
      </div>

      <div className="card">
        <h3>Upload GEDCOM File</h3>
        <input type="file" accept=".ged,.gedcom" onChange={handleFileChange} />
        <button className="btn" onClick={handleImport} disabled={!selectedFile || loading}>
          {loading ? "Importing..." : "Import File"}
        </button>
      </div>

      {importResults && (
        <div className="card">
          <h3>Import Results</h3>
          {importResults.error ? (
            <div style={{ color: "#ef4444" }}>
              <strong>Error:</strong> {importResults.error}
            </div>
          ) : (
            <div>
              <p style={{ color: "#22c55e", fontWeight: "bold", marginBottom: "1rem" }}>
                {importResults.message}
              </p>
              {importResults.data && (
                <>
                  <div style={{ marginBottom: "1rem" }}>
                    <h4>Summary:</h4>
                    <ul style={{ marginLeft: "1.5rem" }}>
                      <li>
                        <strong>Persons:</strong> {importResults.data.persons.filter((p) => p.action === "created").length} created,
                        {" "}{importResults.data.persons.filter((p) => p.action === "updated").length} updated
                      </li>
                      <li>
                        <strong>Families:</strong> {importResults.data.families.filter((f) => f.action === "created").length} created,
                        {" "}{importResults.data.families.filter((f) => f.action === "updated").length} updated
                      </li>
                      <li>
                        <strong>Children linked:</strong> {importResults.data.children.length}
                      </li>
                    </ul>
                  </div>

                  {importResults.data.errors && importResults.data.errors.length > 0 && (
                    <div style={{ marginBottom: "1rem" }}>
                      <h4 style={{ color: "#f59e0b" }}>Warnings ({importResults.data.errors.length}):</h4>
                      <ul style={{
                        marginLeft: "1.5rem",
                        fontSize: "0.9em",
                        maxHeight: "200px",
                        overflowY: "auto",
                        backgroundColor: "#fef3c7",
                        padding: "0.5rem",
                        borderRadius: "4px"
                      }}>
                        {importResults.data.errors.map((err, idx) => (
                          <li key={idx}>{err}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <button
                    className="btn"
                    onClick={handleRollback}
                    disabled={rolling}
                    style={{
                      backgroundColor: "#ef4444",
                      marginTop: "1rem"
                    }}
                  >
                    {rolling ? "Rolling back..." : "Undo Import (Rollback)"}
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
