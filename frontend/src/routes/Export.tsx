import { useState } from "react";
import { exportGedcom } from "../lib/api";
import client from "../lib/api";

export default function ExportPage() {
  const [gedcomPreview, setGedcomPreview] = useState("");
  const [validationResults, setValidationResults] = useState<string[]>([]);
  const [dataLossWarnings, setDataLossWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const handlePreview = async () => {
    setLoading(true);
    try {
      const response = await client.post("/export/gedcom", null, { params: { preview: true } });
      setGedcomPreview(response.data.content);
    } catch (error) {
      console.error("Failed to generate GEDCOM preview:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!gedcomPreview) {
      alert("Please generate a preview first.");
      return;
    }
    setLoading(true);
    try {
      const response = await client.post("/export/validate", { gedcom: gedcomPreview });
      setValidationResults(response.data.errors);
    } catch (error) {
      console.error("Failed to validate GEDCOM:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDataLossCheck = async () => {
    setLoading(true);
    try {
      const response = await client.get("/export/data-loss-warnings");
      const warnings: string[] = [];
      if (response.data.person_fields && response.data.person_fields.length > 0) {
        warnings.push("The following Person fields will not be exported: " + response.data.person_fields.join(", "));
      }
      if (response.data.family_fields && response.data.family_fields.length > 0) {
        warnings.push("The following Family fields will not be exported: " + response.data.family_fields.join(", "));
      }
      setDataLossWarnings(warnings);
    } catch (error) {
      console.error("Failed to get data loss warnings:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    const blob = await exportGedcom();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `genealogy-${new Date().toISOString()}.ged`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <h2>Export</h2>
        <p>
          Export your genealogy data to GEDCOM format. You can preview the GEDCOM file, validate it against the spec, and check for potential data loss before downloading.
        </p>
      </div>

      <div className="card">
        <h3>GEDCOM Preview</h3>
        <div className="grid" style={{ gap: "1rem" }}>
          <button className="btn" onClick={handlePreview} disabled={loading}>
            {loading ? "Generating..." : "Generate Preview"}
          </button>
          <textarea rows={10} value={gedcomPreview} readOnly />
        </div>
      </div>

      <div className="card">
        <h3>GEDCOM Validation</h3>
        <div className="grid" style={{ gap: "1rem" }}>
          <button className="btn" onClick={handleValidate} disabled={!gedcomPreview || loading}>
            {loading ? "Validating..." : "Validate GEDCOM"}
          </button>
          {validationResults.length > 0 ? (
            <ul>
              {validationResults.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          ) : (
            <p>No validation errors found.</p>
          )}
        </div>
      </div>

      <div className="card">
        <h3>Data Loss Warnings</h3>
        <div className="grid" style={{ gap: "1rem" }}>
          <button className="btn" onClick={handleDataLossCheck} disabled={loading}>
            {loading ? "Checking..." : "Check for Data Loss"}
          </button>
          {dataLossWarnings.length > 0 ? (
            <ul>
              {dataLossWarnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          ) : (
            <p>No data loss warnings found.</p>
          )}
        </div>
      </div>

      <div className="card">
        <h3>Download</h3>
        <button className="btn" onClick={handleDownload}>
          Download GEDCOM
        </button>
      </div>
    </div>
  );
}