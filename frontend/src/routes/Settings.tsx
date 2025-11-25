import { useEffect, useState } from "react";
import { getRateLimitSettings, updateRateLimitSettings, type RateLimitSettings } from "../lib/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<RateLimitSettings>({
    enabled: false,
    max_requests_per_minute: 10,
    openrouter_only: true,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await getRateLimitSettings();
      setSettings(data);
    } catch (err) {
      console.error("Failed to load settings:", err);
      setMessage({ type: "error", text: "Failed to load settings" });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);

    try {
      await updateRateLimitSettings(settings);
      setMessage({ type: "success", text: "Settings saved successfully!" });
    } catch (err) {
      console.error("Failed to save settings:", err);
      setMessage({ type: "error", text: "Failed to save settings" });
    } finally {
      setSaving(false);
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
                checked={settings.enabled}
                onChange={(e) => setSettings({ ...settings, enabled: e.target.checked })}
                style={{ width: "18px", height: "18px", cursor: "pointer" }}
              />
              <span style={{ fontWeight: 500 }}>Enable Rate Limiting</span>
            </label>
            <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: "0.25rem", marginLeft: "1.75rem" }}>
              When enabled, limits the number of OpenRouter API requests per minute
            </p>
          </div>

          {/* Max Requests */}
          <div style={{ opacity: settings.enabled ? 1 : 0.5 }}>
            <label style={{ display: "block", fontSize: "0.95rem", fontWeight: 500, marginBottom: "0.5rem" }}>
              Maximum Requests Per Minute
            </label>
            <input
              type="number"
              min="1"
              max="1000"
              value={settings.max_requests_per_minute}
              onChange={(e) => setSettings({ ...settings, max_requests_per_minute: parseInt(e.target.value) || 10 })}
              disabled={!settings.enabled}
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
          <div style={{ opacity: settings.enabled ? 1 : 0.5 }}>
            <label style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              cursor: settings.enabled ? "pointer" : "not-allowed",
              fontSize: "0.95rem"
            }}>
              <input
                type="checkbox"
                checked={settings.openrouter_only}
                onChange={(e) => setSettings({ ...settings, openrouter_only: e.target.checked })}
                disabled={!settings.enabled}
                style={{ width: "18px", height: "18px", cursor: settings.enabled ? "pointer" : "not-allowed" }}
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
            onClick={handleSave}
            disabled={saving}
            style={{ minWidth: "120px" }}
          >
            {saving ? "Saving..." : "Save Settings"}
          </button>

          {message && (
            <div style={{
              padding: "0.5rem 1rem",
              borderRadius: "6px",
              fontSize: "0.9rem",
              backgroundColor: message.type === "success" ? "#dcfce7" : "#fee2e2",
              color: message.type === "success" ? "#166534" : "#991b1b",
              border: `1px solid ${message.type === "success" ? "#bbf7d0" : "#fecaca"}`
            }}>
              {message.text}
            </div>
          )}
        </div>
      </section>

      {/* OpenRouter Info */}
      <section style={{
        backgroundColor: "#f9fafb",
        border: "1px solid #e5e7eb",
        borderRadius: "8px",
        padding: "1.5rem"
      }}>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>
          Current OpenRouter Configuration
        </h2>
        <div style={{ fontSize: "0.9rem", lineHeight: "1.8", color: "#374151" }}>
          <p><strong>Provider:</strong> OpenRouter (Cloud LLM)</p>
          <p><strong>OCR Model:</strong> qwen/qwen2.5-vl-32b-instruct:free</p>
          <p><strong>Parse Model:</strong> meta-llama/llama-3.3-70b-instruct:free (70B!)</p>
          <p><strong>Hybrid OCR:</strong> Enabled (Vision LLM + Tesseract)</p>
          <p><strong>Context Parsing:</strong> Enabled (LLM fallback for ambiguous text)</p>
          <p><strong>Confidence Threshold:</strong> 0.3 (aggressive LLM usage)</p>
        </div>
        <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: "1rem" }}>
          These settings are configured in your <code style={{ backgroundColor: "#e5e7eb", padding: "0.1rem 0.4rem", borderRadius: "3px" }}>.env</code> file.
        </p>
      </section>
    </div>
  );
}
