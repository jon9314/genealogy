import { Navigate, Route, Routes } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import Toolbar from "./components/Toolbar";
import { UndoProvider } from "./hooks/useUndoRedo";
import ExportPage from "./routes/Export";
import GraphPage from "./routes/Graph";
import Home from "./routes/Home";
import OCRPage from "./routes/OCR";
import ParsePage from "./routes/Parse";
import ReviewPage from "./routes/Review";
import TablePage from "./routes/Table";
import Upload from "./routes/Upload";

export default function App() {
  return (
    <UndoProvider>
      <div className="layout">
        <Sidebar />
        <main className="main-content">
          <Toolbar />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/ocr" element={<OCRPage />} />
            <Route path="/parse" element={<ParsePage />} />
            <Route path="/table" element={<TablePage />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/export" element={<ExportPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </UndoProvider>
  );
}
