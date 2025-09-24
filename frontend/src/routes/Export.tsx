import { useState } from "react";

import { exportCsv, exportGedcom } from "../lib/api";

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function ExportPage() {
  const [working, setWorking] = useState(false);

  const handleGedcom = async () => {
    setWorking(true);
    try {
      const blob = await exportGedcom();
      saveBlob(blob, "genealogy.ged");
    } finally {
      setWorking(false);
    }
  };

  const handleCsv = async () => {
    setWorking(true);
    try {
      const blob = await exportCsv();
      saveBlob(blob, "genealogy.csv");
    } finally {
      setWorking(false);
    }
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <h2>Export options</h2>
        <p>GEDCOM 5.5.1 (UTF-8) exports include all individuals and families. CSV exports provide a flat person list.</p>
      </div>
      <div className="grid two">
        <div className="card">
          <h3>GEDCOM</h3>
          <p>Compatible with RootsMagic, Family Tree Maker, and Ancestry.</p>
          <button className="btn" onClick={handleGedcom} disabled={working}>
            {working ? "Preparing..." : "Export GEDCOM"}
          </button>
        </div>
        <div className="card">
          <h3>CSV</h3>
          <p>Imports easily into spreadsheets for auditing.</p>
          <button className="btn" onClick={handleCsv} disabled={working}>
            {working ? "Preparing..." : "Export CSV"}
          </button>
        </div>
      </div>
    </div>
  );
}
