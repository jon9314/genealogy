import { Link } from "react-router-dom";

import { getGedcomPreview } from "../lib/gedcomPreview";
import { useEffect, useState } from "react";

export default function Home() {
  const [preview, setPreview] = useState<string[]>([]);

  useEffect(() => {
    getGedcomPreview().then(setPreview).catch(() => setPreview([]));
  }, []);

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <section className="card">
        <h2>Workflow</h2>
        <ol style={{ lineHeight: 1.8 }}>
          <li>Upload scanned descendancy PDFs</li>
          <li>Run local OCR using OCRmyPDF</li>
          <li>Parse lines into people, spouses, and families</li>
          <li>Review and edit in the grid and graph</li>
          <li>Resolve duplicates</li>
          <li>Export GEDCOM or CSV</li>
        </ol>
      </section>
      <section className="card">
        <h2>Quick links</h2>
        <div className="grid two">
          <Link className="btn secondary" to="/upload">Start with uploads</Link>
          <Link className="btn secondary" to="/table">Open people table</Link>
          <Link className="btn secondary" to="/graph">View family graph</Link>
          <Link className="btn secondary" to="/export">Export data</Link>
        </div>
      </section>
      <section className="card">
        <h2>GEDCOM preview</h2>
        {preview.length ? (
          <pre style={{ background: "rgba(0,0,0,0.25)", padding: "1rem", borderRadius: "8px", maxHeight: "220px", overflow: "auto" }}>
            {preview.join("\n")}
          </pre>
        ) : (
          <p style={{ opacity: 0.7 }}>Generate a GEDCOM export to see the preview.</p>
        )}
      </section>
    </div>
  );
}
