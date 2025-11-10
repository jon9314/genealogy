import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import Toolbar from "./components/Toolbar";
import Notifications from "./components/Notifications";
import { UndoProvider } from "./hooks/useUndoRedo";
import { autosaveProject } from "./lib/api";
import BackupsPage from "./routes/Backups";
import ExportPage from "./routes/Export";
import GraphPage from "./routes/Graph";
import Home from "./routes/Home";
import OCRPage from "./routes/OCR";
import ParsePage from "./routes/Parse";
import ReviewPage from "./routes/Review";
import ReviewOCRPage from "./routes/ReviewOCR";
import SearchPage from "./routes/Search";
import TablePage from "./routes/Table";
import Upload from "./routes/Upload";
import WarningsPage from "./routes/Warnings";
import ImportPage from "./routes/Import";

const AUTOSAVE_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export default function App() {
  const [lastAutosave, setLastAutosave] = useState<Date | null>(null);

  useEffect(() => {
    const performAutosave = async () => {
      try {
        await autosaveProject();
        setLastAutosave(new Date());
      } catch (error) {
        console.error("Autosave failed:", error);
      }
    };

    // Run autosave every 5 minutes
    const interval = setInterval(performAutosave, AUTOSAVE_INTERVAL_MS);

    // Cleanup on unmount
    return () => clearInterval(interval);
  }, []);

  return (
    <UndoProvider>
      <div className="layout">
        <Sidebar />
        <main className="main-content">
          <Toolbar />
          <Notifications />
          {lastAutosave && (
            <div style={{
              position: "fixed",
              bottom: "1rem",
              right: "1rem",
              padding: "0.5rem 0.75rem",
              backgroundColor: "rgba(0, 0, 0, 0.8)",
              borderRadius: "6px",
              fontSize: "0.75rem",
              color: "#22c55e",
              zIndex: 1000
            }}>
              ✓ Auto-saved at {lastAutosave.toLocaleTimeString()}
            </div>
          )}
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/ocr" element={<OCRPage />} />
            <Route path="/review-ocr" element={<ReviewOCRPage />} />
            <Route path="/parse" element={<ParsePage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/table" element={<TablePage />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/warnings" element={<WarningsPage />} />
            <Route path="/backups" element={<BackupsPage />} />
            <Route path="/export" element={<ExportPage />} />
            <Route path="/import" element={<ImportPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </UndoProvider>
  );
}
