import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

const links = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/review-queue", label: "Review Queue" },
  { to: "/evaluation", label: "Evaluation" },
  { to: "/settings", label: "Settings" },
];

export default function NavBar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const token = localStorage.getItem("ai_pr_token");
  const repo = localStorage.getItem("ai_pr_repo");
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications] = useState<string[]>([]);
  const [dark, setDark] = useState(localStorage.getItem("theme") === "dark");

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    localStorage.setItem("theme", next ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", next ? "dark" : "");
  }

  function logout() {
    localStorage.removeItem("ai_pr_token");
    localStorage.removeItem("ai_pr_repo");
    navigate("/connect");
  }

  // Hide on connect, callback, and root — these are standalone pages
  if (pathname === "/connect" || pathname === "/callback" || pathname === "/") return null;
  // Show minimal bar on other unauthenticated pages
  if (!token) return (
    <nav style={{ padding: "8px 24px", borderBottom: "1px solid #e5e7eb", background: "var(--bg-primary)", display: "flex", alignItems: "center" }}>
      <Link to="/connect" style={{ fontWeight: 700, fontSize: 16, color: "#2563eb", textDecoration: "none" }}>AI PR Reviewer</Link>
      <div style={{ flex: 1 }} />
      <button onClick={toggleTheme} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16 }}>{dark ? "☀️" : "🌙"}</button>
    </nav>
  );

  // Full nav for authenticated users
  return (
    <nav style={{
      display: "flex", gap: 4, padding: "8px 24px",
      borderBottom: "1px solid #e5e7eb", background: "var(--bg-primary)",
      position: "sticky", top: 0, zIndex: 10, alignItems: "center",
    }}>
      <Link to="/connect" style={{ fontWeight: 700, fontSize: 16, marginRight: 24, color: "#2563eb", textDecoration: "none" }}>
        AI PR Reviewer
      </Link>
      {links.map((l) => (
        <Link key={l.to} to={l.to} style={{
          padding: "6px 14px", borderRadius: 6, fontSize: 14, textDecoration: "none",
          color: pathname === l.to ? "#fff" : "var(--text-secondary)",
          background: pathname === l.to ? "#2563eb" : "transparent",
        }}>{l.label}</Link>
      ))}
      <div style={{ flex: 1 }} />

      <div style={{ position: "relative", marginRight: 12 }}>
        <button onClick={() => setNotifOpen(!notifOpen)}
          style={{ background: "none", border: "none", cursor: "pointer", fontSize: 18, padding: 4 }}>
          🔔{notifications.length > 0 && <span style={{ position: "absolute", top: -2, right: -2, background: "#dc2626", color: "#fff", borderRadius: "50%", width: 16, height: 16, fontSize: 10, display: "flex", alignItems: "center", justifyContent: "center" }}>{notifications.length}</span>}
        </button>
      </div>

      <span style={{ fontSize: 12, color: "#16a34a", display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#16a34a", display: "inline-block" }} />{repo || "Connected"}
      </span>
      <button onClick={logout} style={{ marginLeft: 12, background: "none", border: "none", color: "#9ca3af", cursor: "pointer", fontSize: 13 }}>Sign Out</button>
      <button onClick={toggleTheme} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16, padding: "4px 8px" }}>{dark ? "☀️" : "🌙"}</button>
    </nav>
  );
}
