import { Link, useLocation } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/review-queue", label: "Review Queue" },
  { to: "/evaluation", label: "Evaluation" },
  { to: "/settings", label: "Settings" },
];

export default function NavBar() {
  const { pathname } = useLocation();

  return (
    <nav style={{
      display: "flex", gap: 4, padding: "8px 24px",
      borderBottom: "1px solid #e5e7eb", background: "#fff",
      position: "sticky", top: 0, zIndex: 10,
    }}>
      <span style={{ fontWeight: 700, fontSize: 16, marginRight: 24, color: "#2563eb" }}>
        AI PR Reviewer
      </span>
      {links.map((l) => (
        <Link
          key={l.to}
          to={l.to}
          style={{
            padding: "6px 14px", borderRadius: 6, fontSize: 14,
            textDecoration: "none",
            color: pathname === l.to ? "#fff" : "#374151",
            background: pathname === l.to ? "#2563eb" : "transparent",
          }}
        >
          {l.label}
        </Link>
      ))}
    </nav>
  );
}
