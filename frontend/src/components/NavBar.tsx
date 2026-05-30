import { Link, useLocation } from "react-router-dom";

const links = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/review-queue", label: "Review Queue" },
  { to: "/evaluation", label: "Evaluation" },
  { to: "/settings", label: "Settings" },
];

export default function NavBar() {
  const { pathname } = useLocation();
  const token = localStorage.getItem("ai_pr_token");
  const repo = localStorage.getItem("ai_pr_repo");
  const [dark, setDark] = useState(localStorage.getItem("theme") === "dark");

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    localStorage.setItem("theme", next ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", next ? "dark" : "");
  }

  return (
    <nav style={{
      display: "flex", gap: 4, padding: "8px 24px",
      borderBottom: "1px solid #e5e7eb", background: "#fff",
      position: "sticky", top: 0, zIndex: 10, alignItems: "center",
    }}>
      <Link to="/connect" style={{ fontWeight: 700, fontSize: 16, marginRight: 24, color: "#2563eb", textDecoration: "none" }}>
        AI PR Reviewer
      </Link>
      {token && links.map((l) => (
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
      <div style={{ flex: 1 }} />
      {token && (
        <span style={{ fontSize: 12, color: "#16a34a", display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#16a34a", display: "inline-block" }} />
          {repo || "Connected"}
        </span>
      )}
      {!token && (
        <Link to="/connect" style={{ fontSize: 13, color: "#2563eb", textDecoration: "none" }}>
          Sign in →
        </Link>
      )}
      <button onClick={toggleTheme}
        style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16, padding: "4px 8px", marginLeft: 4 }}
        title={dark ? "Switch to light mode" : "Switch to dark mode"}>
        {dark ? "☀️" : "🌙"}
      </button>
    </nav>
  );
}
