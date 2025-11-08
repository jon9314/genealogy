import { useEffect, useState } from "react";

import { getOCRText, listSources, updateOCRText, validateOCRText } from "../lib/api";
import type { LineValidation, PageText, Source } from "../lib/types";

export default function ReviewOCRPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [selectedSource, setSelectedSource] = useState<number | null>(null);
  const [pages, setPages] = useState<PageText[]>([]);
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [editedText, setEditedText] = useState("");
  const [validations, setValidations] = useState<LineValidation[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    listSources().then((data) => {
      const ocrDoneSources = data.filter((s) => s.ocr_done);
      setSources(ocrDoneSources);
    });
  }, []);

  useEffect(() => {
    if (selectedSource) {
      loadOCRText(selectedSource);
    }
  }, [selectedSource]);

  useEffect(() => {
    if (pages.length > 0 && currentPageIndex < pages.length) {
      const currentPage = pages[currentPageIndex];
      setEditedText(currentPage.text);
      setHasChanges(false);
      validateText(currentPage.text);
    }
  }, [currentPageIndex, pages]);

  const loadOCRText = async (sourceId: number) => {
    try {
      const data = await getOCRText(sourceId);
      setPages(data);
      setCurrentPageIndex(0);
    } catch (error) {
      console.error("Failed to load OCR text:", error);
      alert("Failed to load OCR text");
    }
  };

  const validateText = async (text: string) => {
    if (!selectedSource) return;
    try {
      const validationResults = await validateOCRText(selectedSource, text);
      setValidations(validationResults);
    } catch (error) {
      console.error("Validation failed:", error);
    }
  };

  const handleTextChange = (newText: string) => {
    setEditedText(newText);
    setHasChanges(true);
    validateText(newText);
  };

  const handleSave = async () => {
    if (!selectedSource || !hasChanges || currentPageIndex >= pages.length) return;

    const currentPage = pages[currentPageIndex];
    setSaving(true);
    try {
      await updateOCRText(selectedSource, currentPage.id, editedText);

      // Update local state
      const updatedPages = [...pages];
      updatedPages[currentPageIndex] = { ...currentPage, text: editedText };
      setPages(updatedPages);
      setHasChanges(false);
      alert("Changes saved successfully!");
    } catch (error) {
      console.error("Save failed:", error);
      alert("Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  const handlePrevPage = () => {
    if (hasChanges) {
      if (!confirm("You have unsaved changes. Discard them?")) return;
    }
    if (currentPageIndex > 0) {
      setCurrentPageIndex(currentPageIndex - 1);
    }
  };

  const handleNextPage = () => {
    if (hasChanges) {
      if (!confirm("You have unsaved changes. Discard them?")) return;
    }
    if (currentPageIndex < pages.length - 1) {
      setCurrentPageIndex(currentPageIndex + 1);
    }
  };

  const invalidLines = validations.filter((v) => !v.is_valid);
  const validLines = validations.filter((v) => v.is_valid);

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <h2>Review & Edit OCR Text</h2>
        <p>Review OCR text before parsing. Edit any errors and see which lines match expected patterns.</p>
      </div>

      {!selectedSource ? (
        <div className="card">
          <h3>Select a source to review</h3>
          <div className="grid" style={{ gap: "0.75rem", marginTop: "1rem" }}>
            {sources.map((source) => (
              <button
                key={source.id}
                className="btn secondary"
                onClick={() => setSelectedSource(source.id)}
                style={{ textAlign: "left", justifyContent: "flex-start" }}
              >
                {source.name} <span className="badge" style={{ marginLeft: "0.5rem" }}>{source.pages} pages</span>
              </button>
            ))}
            {sources.length === 0 && <p>No sources with OCR completed yet.</p>}
          </div>
        </div>
      ) : (
        <>
          <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong>{sources.find((s) => s.id === selectedSource)?.name}</strong>
              <span style={{ marginLeft: "1rem", opacity: 0.7 }}>
                Page {currentPageIndex + 1} of {pages.length}
              </span>
            </div>
            <button className="btn secondary" onClick={() => setSelectedSource(null)}>
              Change Source
            </button>
          </div>

          <div className="grid two" style={{ gap: "1.5rem", alignItems: "start" }}>
            {/* Editor */}
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ margin: 0 }}>Edit Text</h3>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    className="btn secondary"
                    onClick={handlePrevPage}
                    disabled={currentPageIndex === 0}
                  >
                    ← Prev
                  </button>
                  <button
                    className="btn secondary"
                    onClick={handleNextPage}
                    disabled={currentPageIndex >= pages.length - 1}
                  >
                    Next →
                  </button>
                </div>
              </div>

              <textarea
                value={editedText}
                onChange={(e) => handleTextChange(e.target.value)}
                rows={20}
                style={{
                  fontFamily: "monospace",
                  fontSize: "0.9rem",
                  lineHeight: "1.6",
                  resize: "vertical",
                }}
              />

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontSize: "0.85rem", opacity: 0.7 }}>
                  {hasChanges && "● Unsaved changes"}
                </div>
                <button
                  className="btn"
                  onClick={handleSave}
                  disabled={!hasChanges || saving}
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </div>

            {/* Validation Results */}
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <h3 style={{ margin: 0 }}>Pattern Validation</h3>

              <div style={{ display: "flex", gap: "1rem", fontSize: "0.9rem" }}>
                <div style={{ color: "#22c55e" }}>
                  ✓ Valid: {validLines.length}
                </div>
                <div style={{ color: "#ef4444" }}>
                  ✗ Invalid: {invalidLines.length}
                </div>
              </div>

              {invalidLines.length > 0 && (
                <details open>
                  <summary style={{ cursor: "pointer", fontWeight: 600, marginBottom: "0.5rem" }}>
                    Invalid Lines ({invalidLines.length})
                  </summary>
                  <div style={{ maxHeight: "400px", overflowY: "auto", fontSize: "0.85rem" }}>
                    {invalidLines.map((v) => (
                      <div
                        key={v.line_number}
                        style={{
                          padding: "0.5rem",
                          marginBottom: "0.25rem",
                          backgroundColor: "rgba(239, 68, 68, 0.1)",
                          borderLeft: "3px solid #ef4444",
                          borderRadius: "4px",
                          fontFamily: "monospace",
                        }}
                      >
                        <div style={{ color: "#ef4444", fontSize: "0.75rem", marginBottom: "0.25rem" }}>
                          Line {v.line_number}
                        </div>
                        <div>{v.text}</div>
                      </div>
                    ))}
                  </div>
                </details>
              )}

              {validLines.length > 0 && (
                <details>
                  <summary style={{ cursor: "pointer", fontWeight: 600, marginBottom: "0.5rem" }}>
                    Valid Lines ({validLines.length})
                  </summary>
                  <div style={{ maxHeight: "300px", overflowY: "auto", fontSize: "0.85rem" }}>
                    {validLines.map((v) => (
                      <div
                        key={v.line_number}
                        style={{
                          padding: "0.5rem",
                          marginBottom: "0.25rem",
                          backgroundColor: "rgba(34, 197, 94, 0.1)",
                          borderLeft: "3px solid #22c55e",
                          borderRadius: "4px",
                          fontFamily: "monospace",
                        }}
                      >
                        <div style={{ color: "#22c55e", fontSize: "0.75rem", marginBottom: "0.25rem" }}>
                          Line {v.line_number} • {v.pattern_type === "person" ? "Person" : "Spouse"}
                        </div>
                        <div>{v.text}</div>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
