import { BrowserRouter, Routes, Route } from "react-router-dom";
import NavBar from "./components/NavBar";
import Connect from "./pages/Connect";
import Dashboard from "./pages/Dashboard";
import ReviewQueue from "./pages/ReviewQueue";
import ReviewWorkspace from "./pages/ReviewWorkspace";
import EvaluationCenter from "./pages/EvaluationCenter";
import Settings from "./pages/Settings";

function OAuthCallback() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");
  if (code) {
    fetch(`http://localhost:8000/api/v1/auth/callback?code=${code}`, { method: "POST" })
      .then(r => r.json())
      .then(d => {
        if (d.access_token) {
          localStorage.setItem("ai_pr_token", d.access_token);
          window.location.href = "/connect";
        } else {
          window.location.href = "/connect?error=" + encodeURIComponent(d.error || "oauth_failed");
        }
      })
      .catch(() => {
        window.location.href = "/connect?error=api_unreachable";
      });
    return <p style={{ padding: 40, textAlign: "center" }}>Completing sign in...</p>;
  }
  return <p style={{ padding: 40, textAlign: "center", color: "#dc2626" }}>Authentication failed.</p>;
}

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<Connect />} />
        <Route path="/connect" element={<Connect />} />
        <Route path="/callback" element={<OAuthCallback />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/review-queue" element={<ReviewQueue />} />
        <Route path="/review/:owner/:repo/:number" element={<ReviewWorkspace />} />
        <Route path="/evaluation" element={<EvaluationCenter />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </BrowserRouter>
  );
}
