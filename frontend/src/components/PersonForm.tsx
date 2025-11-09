import { FormEvent, useState } from "react";

import { listSources } from "../lib/api";
import type { Person, UpdatePersonPayload } from "../lib/types";

interface Props {
  person: Person;
  onSubmit: (payload: UpdatePersonPayload) => Promise<void> | void;
  onClose: () => void;
}

export default function PersonForm({ person, onSubmit, onClose }: Props) {
  const [form, setForm] = useState<UpdatePersonPayload>({
    name: person.name,
    given: person.given,
    surname: person.surname,
    birth: person.birth,
    death: person.death,
    title: person.title,
    sex: person.sex,
    notes: person.notes,
    chart_id: person.chart_id,
  });
  const [saving, setSaving] = useState(false);

  const handleChange = (key: keyof UpdatePersonPayload, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value || null }));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await onSubmit(form);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card" style={{ minWidth: "360px" }}>
      <form onSubmit={handleSubmit} className="grid" style={{ gap: "0.75rem" }}>
        {person.source_id != null && (person.page_index != null || person.line_index != null) && (
          <div style={{
            padding: "0.75rem",
            backgroundColor: "rgba(79, 156, 255, 0.1)",
            border: "1px solid rgba(79, 156, 255, 0.3)",
            borderRadius: "6px",
            fontSize: "0.85rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "1rem"
          }}>
            <div>
              <strong>📄 Source Citation:</strong> Source ID {person.source_id}
              {person.page_index != null && ` • Page ${person.page_index + 1}`}
              {person.line_index != null && ` • Line ${person.line_index + 1}`}
            </div>
            <a
              href={`/api/files/${person.source_id}/pdf#page=${(person.page_index ?? 0) + 1}`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn secondary"
              style={{ fontSize: "0.75rem", padding: "0.35rem 0.75rem" }}
            >
              View Source →
            </a>
          </div>
        )}
        <div>
          <label>Name</label>
          <input value={form.name ?? ""} onChange={(e) => handleChange("name", e.target.value)} required />
        </div>
        <div className="grid two">
          <div>
            <label>Given</label>
            <input value={form.given ?? ""} onChange={(e) => handleChange("given", e.target.value)} />
          </div>
          <div>
            <label>Surname</label>
            <input value={form.surname ?? ""} onChange={(e) => handleChange("surname", e.target.value)} />
          </div>
        </div>
        <div className="grid two">
          <div>
            <label>Birth</label>
            <input value={form.birth ?? ""} onChange={(e) => handleChange("birth", e.target.value)} />
          </div>
          <div>
            <label>Death</label>
            <input value={form.death ?? ""} onChange={(e) => handleChange("death", e.target.value)} />
          </div>
        </div>
        <div className="grid two">
          <div>
            <label>Sex</label>
            <select value={form.sex ?? ""} onChange={(e) => handleChange("sex", e.target.value)}>
              <option value="">Unknown</option>
              <option value="M">Male</option>
              <option value="F">Female</option>
            </select>
          </div>
          <div>
            <label>Title</label>
            <input value={form.title ?? ""} onChange={(e) => handleChange("title", e.target.value)} />
          </div>
        </div>
        <div>
          <label>Chart ID</label>
          <input value={form.chart_id ?? ""} onChange={(e) => handleChange("chart_id", e.target.value)} />
        </div>
        <div>
          <label>Notes</label>
          <textarea rows={4} value={form.notes ?? ""} onChange={(e) => handleChange("notes", e.target.value)} />
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
          <button type="button" className="btn secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn" disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}
