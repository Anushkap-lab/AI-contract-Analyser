import { useState } from "react"
import { useAuth } from "../hooks/useAuth"
import { register } from "../services/auth"

export default function AuthPage() {
  const { login } = useAuth()
  const [mode, setMode]       = useState("login")  // "login" | "register"
  const [email, setEmail]     = useState("")
  const [password, setPassword] = useState("")
  const [name, setName]       = useState("")
  const [error, setError]     = useState("")
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setError("")
    setLoading(true)
    try {
      if (mode === "register") {
        await register(email, password, name)
        // auto-login after register
        await login(email, password)
      } else {
        await login(email, password)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: "100vh", background: "var(--bg)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: "1rem"
    }}>
      <div style={{
        width: "100%", maxWidth: 400,
        background: "var(--surface)", borderRadius: 16,
        border: ".5px solid var(--border)", padding: "2rem"
      }}>
        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: "1.5rem" }}>
          <div className="brand-icon"><i className="ti ti-scale" /></div>
          <div>
            <div className="brand-name">LexaAI</div>
            <div className="brand-sub">Contract Intelligence</div>
          </div>
        </div>

        <h2 style={{
          fontFamily: "'Playfair Display', serif", fontSize: 20,
          fontWeight: 500, marginBottom: 6, color: "var(--text)"
        }}>
          {mode === "login" ? "Welcome back" : "Create account"}
        </h2>
        <p style={{ fontSize: 13, color: "var(--text2)", marginBottom: "1.5rem" }}>
          {mode === "login"
            ? "Sign in to continue analysing contracts"
            : "Start analysing contracts with AI"}
        </p>

        {error && (
          <div className="error-box" style={{ marginBottom: "1rem" }}>{error}</div>
        )}

        {mode === "register" && (
          <div style={{ marginBottom: 10 }}>
            <label style={{ fontSize: 12, color: "var(--text3)", display: "block", marginBottom: 4 }}>
              Full Name
            </label>
            <input
              className="ask-input" style={{ width: "100%" }}
              placeholder="Jane Smith"
              value={name} onChange={e => setName(e.target.value)}
            />
          </div>
        )}

        <div style={{ marginBottom: 10 }}>
          <label style={{ fontSize: 12, color: "var(--text3)", display: "block", marginBottom: 4 }}>
            Email
          </label>
          <input
            className="ask-input" style={{ width: "100%" }}
            type="email" placeholder="you@company.com"
            value={email} onChange={e => setEmail(e.target.value)}
          />
        </div>

        <div style={{ marginBottom: "1.25rem" }}>
          <label style={{ fontSize: 12, color: "var(--text3)", display: "block", marginBottom: 4 }}>
            Password
          </label>
          <input
            className="ask-input" style={{ width: "100%" }}
            type="password" placeholder="Min. 8 characters"
            value={password} onChange={e => setPassword(e.target.value)}
            onKeyDown={e => e.key === "Enter" && submit()}
          />
        </div>

        <button
          className="ask-btn" style={{ width: "100%", justifyContent: "center" }}
          onClick={submit} disabled={loading}
        >
          {loading
            ? <i className="ti ti-loader spin" />
            : <i className="ti ti-arrow-right" />}
          {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
        </button>

        <p style={{ textAlign: "center", fontSize: 13, color: "var(--text3)", marginTop: "1rem" }}>
          {mode === "login" ? "Don't have an account? " : "Already have an account? "}
          <span
            style={{ color: "var(--navy)", cursor: "pointer", fontWeight: 500 }}
            onClick={() => { setMode(mode === "login" ? "register" : "login"); setError("") }}
          >
            {mode === "login" ? "Sign up" : "Sign in"}
          </span>
        </p>
      </div>
    </div>
  )
}