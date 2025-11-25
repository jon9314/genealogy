import { useEffect, useState } from "react";
import {
  getRateLimitSettings,
  updateRateLimitSettings,
  type RateLimitSettings,
  getOpenRouterModels,
  getOpenRouterSettings,
  updateOpenRouterSettings,
  type ModelInfo,
  type OpenRouterSettings
} from "../lib/api";

export default function SettingsPage() {
  const [rateLimitSettings, setRateLimitSettings] = useState<RateLimitSettings>({
    enabled: false,
    max_requests_per_minute: 10,
    openrouter_only: true,
  });
  const [openRouterSettings, setOpenRouterSettings] = useState<OpenRouterSettings>({
    ocr_model: "",
    parse_model: "",
    use_hybrid_ocr: false,
    use_context_parse: false,
    confidence_threshold: 0.7,
  });
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingRate, setSavingRate] = useState(false);
  const [savingOpenRouter, setSavingOpenRouter] = useState(false);
  const [rateMessage, setRateMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [openRouterMessage, setOpenRouterMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [rateData, openRouterData, modelsData] = await Promise.all([
        getRateLimitSettings(),
        getOpenRouterSettings(),
        getOpenRouterModels().catch(() => [] as ModelInfo[])
      ]);
      setRateLimitSettings(rateData);
      setOpenRouterSettings(openRouterData);
      setModels(modelsData);
    } catch (err) {
      console.error("Failed to load settings:", err);
      setRateMessage({ type: "error", text: "Failed to load settings" });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRateLimit = async () => {
    setSavingRate(true);
    setRateMessage(null);

    try {
      await updateRateLimitSettings(rateLimitSettings);
      setRateMessage({ type: "success", text: "Rate limit settings saved successfully!" });
    } catch (err) {
      console.error("Failed to save rate limit settings:", err);
      setRateMessage({ type: "error", text: "Failed to save settings" });
    } finally {
      setSavingRate(false);
    }
  };

  const handleSaveOpenRouter = async () => {
    setSavingOpenRouter(true);
    setOpenRouterMessage(null);

    try {
      await updateOpenRouterSettings(openRouterSettings);
      setOpenRouterMessage({ type: "success", text: "OpenRouter settings saved! Restart server to apply changes." });
    } catch (err) {
      console.error("Failed to save OpenRouter settings:", err);
      setOpenRouterMessage({ type: "error", text: "Failed to save settings" });
    } finally {
      setSavingOpenRouter(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "2rem" }}>
        <p>Loading settings...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "800px" }}>
      <h1 style={{ marginBottom: "1.5rem" }}>Application Settings</h1>

      {/* Rate Limiting Section */}
      <section style={{
        backgroundColor: "white",
        border: "1px solid #e5e7eb",
        borderRadius: "8px",
        padding: "1.5rem",
        marginBottom: "1.5rem"
      }}>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>
          OpenRouter API Rate Limiting
        </h2>

        <p style={{ fontSize: "0.9rem", color: "#6b7280", marginBottom: "1.5rem" }}>
          Configure rate limiting to control OpenRouter LLM API usage and avoid hitting free tier limits.
          Rate limiting is <strong>disabled by default</strong> but can be enabled if needed.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Enable/Disable */}
          <div>
            <label style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              cursor: "pointer",
              fontSize: "0.95rem"
            }}>
              <input
                type="checkbox"
                checked={rateLimitSettings.enabled}
                onChange={(e) => setRateLimitSettings({ ...rateLimitSettings, enabled: e.target.checked })}
                style={{ width: "18px", height: "18px", cursor: "pointer" }}
              />
              <span style={{ fontWeight: 500 }}>Enable Rate Limiting</span>
            </label>
            <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: "0.25rem", marginLeft: "1.75rem" }}>
              When enabled, limits the number of OpenRouter API requests per minute
            </p>
          </div>

          {/* Max Requests */}
          <div style={{ opacity: rateLimitSettings.enabled ? 1 : 0.5 }}>
            <label style={{ display: "block", fontSize: "0.95rem", fontWeight: 500, marginBottom: "0.5rem" }}>
              Maximum Requests Per Minute
            </label>
            <input
              type="number"
              min="1"
              max="1000"
              value={rateLimitSettings.max_requests_per_minute}
              onChange={(e) => setRateLimitSettings({ ...rateLimitSettings, max_requests_per_minute: parseInt(e.target.value) || 10 })}
              disabled={!rateLimitSettings.enabled}
              style={{
                width: "150px",
                padding: "0.5rem",
                fontSize: "0.95rem",
                border: "1px solid #d1d5db",
                borderRadius: "6px"
              }}
            />
            <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: "0.25rem" }}>
              Recommended: 10-20 for free tier, 100+ for paid accounts
            </p>
          </div>

          {/* OpenRouter Only */}
          <div style={{ opacity: rateLimitSettings.enabled ? 1 : 0.5 }}>
            <label style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              cursor: rateLimitSettings.enabled ? "pointer" : "not-allowed",
              fontSize: "0.95rem"
            }}>
              <input
                type="checkbox"
                checked={rateLimitSettings.openrouter_only}
                onChange={(e) => setRateLimitSettings({ ...rateLimitSettings, openrouter_only: e.target.checked })}
                disabled={!rateLimitSettings.enabled}
                style={{ width: "18px", height: "18px", cursor: rateLimitSettings.enabled ? "pointer" : "not-allowed" }}
              />
              <span style={{ fontWeight: 500 }}>Apply to OpenRouter API Only</span>
            </label>
            <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: "0.25rem", marginLeft: "1.75rem" }}>
              When checked, rate limit only applies to LLM calls (OCR correction and parsing).
              Other API calls are not affected.
            </p>
          </div>
        </div>

        {/* Info Box */}
        <div style={{
          marginTop: "1.5rem",
          padding: "1rem",
          backgroundColor: "#eff6ff",
          border: "1px solid #bfdbfe",
          borderRadius: "6px"
        }}>
          <h3 style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.5rem", color: "#1e40af" }}>
            💡 About Rate Limiting
          </h3>
          <ul style={{ fontSize: "0.85rem", color: "#1e3a8a", marginLeft: "1.25rem", lineHeight: "1.6" }}>
            <li>Free tier models have built-in rate limits from OpenRouter</li>
            <li>Enable this setting to add an additional application-level limit</li>
            <li>Useful when processing many documents in batch</li>
            <li>If you hit a rate limit, the app will fallback to regex parsing</li>
            <li>Disabled by default - only enable if you're hitting rate limits</li>
          </ul>
        </div>

        {/* Save Button */}
        <div style={{ marginTop: "1.5rem", display: "flex", gap: "1rem", alignItems: "center" }}>
          <button
            className="btn"
            onClick={handleSaveRateLimit}
            disabled={savingRate}
            style={{ minWidth: "120px" }}
          >
            {savingRate ? "Saving..." : "Save Settings"}
          </button>

          {rateMessage && (
            <div style={{
              padding: "0.5rem 1rem",
              borderRadius: "6px",
              fontSize: "0.9rem",
              backgroundColor: rateMessage.type === "success" ? "#dcfce7" : "#fee2e2",
              color: rateMessage.type === "success" ? "#166534" : "#991b1b",
              border: `1px solid ${rateMessage.type === "success" ? "#bbf7d0" : "#fecaca"}`
            }}>
              {rateMessage.text}
            </div>
          )}
        </div>
      </section>

      {/* OpenRouter Configuration */}
      <section style={{
        backgroundColor: "white",
        border: "1px solid #e5e7eb",
        borderRadius: "8px",
        padding: "1.5rem",
        marginBottom: "1.5rem"
      }}>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>
          OpenRouter LLM Configuration
        </h2>

        <p style={{ fontSize: "0.9rem", color: "#6b7280", marginBottom: "1.5rem" }}>
          Configure which models to use for OCR and parsing, and control LLM behavior.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* OCR Model Selection */}
          <div>
            <label style={{ display: "block", fontSize: "0.95rem", fontWeight: 500, marginBottom: "0.5rem" }}>
              OCR Model (Vision)
            </label>
            <select
              value={openRouterSettings.ocr_model}
              onChange={(e) => setOpenRouterSettings({ ...openRouterSettings, ocr_model: e.target.value })}
              style={{
                width: "100%",
                padding: "0.5rem",
                fontSize: "0.95rem",
                border: "1px solid #d1d5db",
                borderRadius: "6px",
                backgroundColor: "white"
              }}
            >
              {models.filter(m => m.is_vision).length === 0 && (
                <option value="">Loading models...</option>
              )}
              {models.filter(m => m.is_vision).map(model => (
                <option key={model.id} value={model.id}>
                  {model.name} ({model.id})
                </option>
              ))}
            </select>
            <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: "0.25rem" }}>
              Vision model used for OCR correction and image analysis
            </p>
          </div>

          {/* Parse Model Selection */}
          <div>
            <label style={{ display: "block", fontSize: "0.95rem", fontWeight: 500, marginBottom: "0.5rem" }}>
              Parse Model (Text)
            </label>
            <select
              value={openRouterSettings.parse_model}
              onChange={(e) => setOpenRouterSettings({ ...openRouterSettings, parse_model: e.target.value })}
              style={{
                width: "100%",
                padding: "0.5rem",
                fontSize: "0.95rem",
                border: "1px solid #d1d5db",
                borderRadius: "6px",
                backgroundColor: "white"
              }}
            >
              {models.filter(m => !m.is_vision).length === 0 && (
                <option value="">Loading models...</option>
              )}
              {models.filter(m => !m.is_vision).map(model => (
                <option key={model.id} value={model.id}>
                  {model.name} ({model.id})
                </option>
              ))}
            </select>
            <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: "0.25rem" }}>
              Text model used for parsing genealogy data
            </p>
          </div>

          {/* Hybrid OCR Toggle */}
          <div>
            <label style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              cursor: "pointer",
              fontSize: "0.95rem"
            }}>
              <input
                type="checkbox"
                checked={openRouterSettings.use_hybrid_ocr}
                onChange={(e) => setOpenRouterSettings({ ...openRouterSettings, use_hybrid_ocr: e.target.checked })}
                style={{ width: "18px", height: "18px", cursor: "pointer" }}
              />
              <span style={{ fontWeight: 500 }}>Enable Hybrid OCR</span>
            </label>
            <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: "0.25rem", marginLeft: "1.75rem" }}>
              Use both Tesseract and Vision LLM for OCR, comparing results line-by-line
            </p>
          </div>

          {/* Context Parse Toggle */}
          <div>
            <label style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              cursor: "pointer",
              fontSize: "0.95rem"
            }}>
              <input
                type="checkbox"
                checked={openRouterSettings.use_context_parse}
                onChange={(e) => setOpenRouterSettings({ ...openRouterSettings, use_context_parse: e.target.checked })}
                style={{ width: "18px", height: "18px", cursor: "pointer" }}
              />
              <span style={{ fontWeight: 500 }}>Enable Context Parsing</span>
            </label>
            <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: "0.25rem", marginLeft: "1.75rem" }}>
              Use LLM fallback when regex patterns fail to parse genealogy text
            </p>
          </div>

          {/* Confidence Threshold */}
          <div>
            <label style={{ display: "block", fontSize: "0.95rem", fontWeight: 500, marginBottom: "0.5rem" }}>
              OCR Confidence Threshold: {openRouterSettings.confidence_threshold.toFixed(2)}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={openRouterSettings.confidence_threshold}
              onChange={(e) => setOpenRouterSettings({ ...openRouterSettings, confidence_threshold: parseFloat(e.target.value) })}
              style={{ width: "100%" }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "#6b7280", marginTop: "0.25rem" }}>
              <span>0.0 (always use LLM)</span>
              <span>1.0 (never use LLM)</span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: "0.5rem" }}>
              Lower values = more aggressive LLM usage. Recommended: 0.3 for free tier, 0.7 for balanced
            </p>
          </div>
        </div>

        {/* Save Button */}
        <div style={{ marginTop: "1.5rem", display: "flex", gap: "1rem", alignItems: "center" }}>
          <button
            className="btn"
            onClick={handleSaveOpenRouter}
            disabled={savingOpenRouter}
            style={{ minWidth: "120px" }}
          >
            {savingOpenRouter ? "Saving..." : "Save OpenRouter Settings"}
          </button>

          {openRouterMessage && (
            <div style={{
              padding: "0.5rem 1rem",
              borderRadius: "6px",
              fontSize: "0.9rem",
              backgroundColor: openRouterMessage.type === "success" ? "#dcfce7" : "#fee2e2",
              color: openRouterMessage.type === "success" ? "#166534" : "#991b1b",
              border: `1px solid ${openRouterMessage.type === "success" ? "#bbf7d0" : "#fecaca"}`
            }}>
              {openRouterMessage.text}
            </div>
          )}
        </div>

        {/* Info */}
        <div style={{
          marginTop: "1.5rem",
          padding: "1rem",
          backgroundColor: "#eff6ff",
          border: "1px solid #bfdbfe",
          borderRadius: "6px"
        }}>
          <p style={{ fontSize: "0.85rem", color: "#1e3a8a", margin: 0 }}>
            <strong>Note:</strong> Settings are saved to your .env file but require a server restart to fully apply.
            Changes take effect immediately for new requests but existing processes use cached settings.
          </p>
        </div>
      </section>
    </div>
  );
}
