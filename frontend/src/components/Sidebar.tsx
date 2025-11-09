import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Overview" },
  { to: "/upload", label: "Upload" },
  { to: "/ocr", label: "OCR" },
  { to: "/review-ocr", label: "Review OCR" },
  { to: "/parse", label: "Parse" },
  { to: "/table", label: "Table" },
  { to: "/graph", label: "Graph" },
  { to: "/review", label: "Review Duplicates" },
  { to: "/warnings", label: "Validation Warnings" },
  { to: "/export", label: "Export" },
];

export default function Sidebar() {
  return (
    <aside style={{ background: "rgba(0,0,0,0.45)", padding: "1.5rem", borderRight: "1px solid rgba(255,255,255,0.05)" }}>
      <div style={{ fontWeight: 700, fontSize: "1.2rem", marginBottom: "2rem" }}>Genealogy Workbench</div>
      <nav className="grid" style={{ gap: "0.5rem" }}>
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) =>
              `card` + (isActive ? " active" : "")
            }
            style={({ isActive }) => ({
              background: isActive ? "rgba(79, 156, 255, 0.15)" : "rgba(255,255,255,0.05)",
              border: isActive ? "1px solid rgba(79,156,255,0.6)" : "1px solid rgba(255,255,255,0.05)",
              padding: "0.75rem 1rem",
              borderRadius: "10px",
              transition: "background 120ms ease",
            })}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
