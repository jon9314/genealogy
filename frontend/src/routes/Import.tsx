import { useState } from "react";
import client from "../lib/api";

export default function ImportPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importResults, setImportResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setSelectedFile(event.target.files[0]);
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
    } catch (error) {
      console.error("Failed to import GEDCOM file:", error);
      setImportResults({ error: "Failed to import GEDCOM file." });
    } finally {
      setLoading(false);
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
      </div>

      <div className="card">
        <h3>Upload GEDCOM File</h3>
        <input type="file" accept=".ged" onChange={handleFileChange} />
        <button className="btn" onClick={handleImport} disabled={!selectedFile || loading}>
          {loading ? "Importing..." : "Import File"}
        </button>
      </div>

      {importResults && (
        <div className="card">
          <h3>Import Results</h3>
          {importResults.error ? (
            <p style={{ color: "red" }}>Error: {importResults.error}</p>
          ) : (
            <div>
              <p>{importResults.message}</p>
              {importResults.data && (
                <ul>
                  <li>Persons Created: {importResults.data.persons.filter((p: any) => p.action === "created").length}</li>
                  <li>Persons Updated: {importResults.data.persons.filter((p: any) => p.action === "updated").length}</li>
                  <li>Families Created: {importResults.data.families.filter((f: any) => f.action === "created").length}</li>
                  <li>Families Updated: {importResults.data.families.filter((f: any) => f.action === "updated").length}</li>
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
