import "../styles/login.css"
import axios from "axios";
import { Scale } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await axios.post("http://127.0.0.1:8000/login", {
        email,
        password,
      });

      localStorage.setItem("token", res.data.token);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed. Check your email and password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell auth-shell">
      <section className="auth-panel">
        <div className="auth-brand">
          <div className="brand-icon">
            <Scale size={22} strokeWidth={1.9} />
          </div>
          <div>
            <h1 className="brand-name">LexaAI</h1>
            <p className="brand-sub">Contract Intelligence</p>
          </div>
        </div>

        <form className="auth-form" onSubmit={handleLogin}>
          <div>
            <h2>Login</h2>
            <p>Access your contract analysis dashboard.</p>
          </div>

          <label>
            Email
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>

          {error && <p className="error-box">{error}</p>}

          <button className="auth-button" type="submit" disabled={loading}>
            {loading ? "Logging in..." : "Login"}
          </button>

          <p className="auth-link">
            New to LexaAI? <Link to="/register">Create an account</Link>
          </p>
        </form>
      </section>
    </main>
  );
}
