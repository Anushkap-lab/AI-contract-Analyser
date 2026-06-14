import { useState } from "react"
import { useAuth } from "../hooks/useAuth.jsx"
import { register } from "../services/api"

export default function AuthPage() {
  const { login }                     = useAuth()
  const [mode, setMode]               = useState("login")
  const [email, setEmail]             = useState("")
  const [password, setPassword]       = useState("")
  const [name, setName]               = useState("")
  const [error, setError]             = useState("")
  const [loading, setLoading]         = useState(false)

  const submit = async () => {
    setError("")
    setLoading(true)
    try {
      if (mode === "register") {
        await register(email, password, name)
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

  const switchMode = () => {
    setMode(mode === "login" ? "register" : "login")
    setError("")
  }

  return (
    <div className="auth-shell">
      <div className={`auth-card ${mode === "register" ? "register" : ""}`}>

        {/* Brand */}
        <div className="auth-brand">
          <div className="brand-icon">
            <i className="ti ti-scale" style={{ fontSize: 20 }} />
          </div>
          <div>
            <div className="brand-name">LexaAI</div>
            <div className="brand-sub">Contract Intelligence</div>
          </div>
        </div>

        {/* Heading */}
        <h2 className="auth-heading">
          {mode === "login" ? "Welcome back" : "Create account"}
        </h2>
        <p className="auth-subheading">
          {mode === "login"
            ? "Sign in to continue analysing contracts"
            : "Start analysing contracts with AI"}
        </p>

        {/* Error */}
        {error && <div className="auth-error">{error}</div>}

        {/* Full name — register only */}
        {mode === "register" && (
          <div className="auth-field">
            <label>Full Name</label>
            <input
              placeholder="Jane Smith"
              value={name}
              onChange={e => setName(e.target.value)}
            />
          </div>
        )}

        {/* Email */}
        <div className="auth-field">
          <label>Email</label>
          <input
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={e => setEmail(e.target.value)}
          />
        </div>

        {/* Password */}
        <div className="auth-field">
          <label>Password</label>
          <input
            type="password"
            placeholder="Min. 8 characters"
            value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyDown={e => e.key === "Enter" && submit()}
          />
        </div>

        {/* Submit */}
        <button className="auth-btn" onClick={submit} disabled={loading}>
          {loading
            ? <><span className="auth-spinner" /> Please wait...</>
            : <>{mode === "login" ? "Sign In" : "Create Account"}</>}
        </button>

        {/* Toggle mode */}
        <p className="auth-footer">
          {mode === "login" ? "Don't have an account? " : "Already have an account? "}
          <span onClick={switchMode}>
            {mode === "login" ? "Sign up" : "Sign in"}
          </span>
        </p>

      </div>
    </div>
  )
}
