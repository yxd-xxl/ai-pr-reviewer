import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

const API = "http://localhost:8000";

export default function Register() {
  const navigate = useNavigate();
  const [method, setMethod] = useState<"email" | "phone">("email");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRegister() {
    setError(""); setLoading(true);
    try {
      const body: any = { password, name };
      if (method === "email") body.email = email;
      else body.phone = phone;
      const r = await fetch(`${API}/api/v1/auth/register`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      const d = await r.json();
      if (d.access_token) {
        localStorage.setItem("ai_pr_token", d.access_token);
        localStorage.setItem("ai_pr_new_user", "true");
        navigate("/onboarding");
      } else {
        setError(d.error || "Registration failed");
      }
    } catch { setError("Cannot reach API server."); }
    setLoading(false);
  }

  return (
    <div style={{ maxWidth: 440, margin: "60px auto", padding: 32 }}>
      <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 4 }}>Create Account</h1>
      <p style={{ color: "#6b7280", marginBottom: 24 }}>Register to start reviewing PRs with AI.</p>
      {error && <div style={{ padding: 10, background: "#fee2e2", color: "#dc2626", borderRadius: 6, marginBottom: 16, fontSize: 13 }}>{error}</div>}

      <div style={{ display: "flex", marginBottom: 20, borderRadius: 8, overflow: "hidden", border: "1px solid #d1d5db" }}>
        <button onClick={() => setMethod("email")}
          style={{ flex: 1, padding: 10, border: "none", cursor: "pointer", fontSize: 14, background: method === "email" ? "#2563eb" : "#fff", color: method === "email" ? "#fff" : "#374151" }}>Email</button>
        <button onClick={() => setMethod("phone")}
          style={{ flex: 1, padding: 10, border: "none", cursor: "pointer", fontSize: 14, background: method === "phone" ? "#2563eb" : "#fff", color: method === "phone" ? "#fff" : "#374151" }}>Phone</button>
      </div>

      <input value={name} onChange={e => setName(e.target.value)} placeholder="Name (optional)"
        style={inputStyle} />

      {method === "email" ? (
        <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email address"
          style={inputStyle} />
      ) : (
        <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} placeholder="Phone number"
          style={inputStyle} />
      )}

      <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password (min 6 characters)"
        style={inputStyle} />

      <button onClick={handleRegister} disabled={loading || !password || (!email && !phone)}
        style={{ width: "100%", padding: 12, borderRadius: 8, border: "none", fontSize: 16, fontWeight: 600, cursor: (password && (email || phone)) ? "pointer" : "default", background: (password && (email || phone)) ? "#2563eb" : "#d1d5db", color: "#fff", marginTop: 8 }}>
        {loading ? "Creating account..." : "Create Account"}
      </button>

      <div style={{ marginTop: 24, textAlign: "center", fontSize: 14, color: "#6b7280" }}>
        Already have an account? <Link to="/login" style={{ color: "#2563eb" }}>Sign in</Link>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "10px 14px", fontSize: 14, borderRadius: 6, border: "1px solid #d1d5db", marginBottom: 12, boxSizing: "border-box",
};
