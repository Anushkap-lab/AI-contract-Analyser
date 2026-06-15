import { useAuth } from "../hooks/useAuth.jsx"

export default function Topbar() {
  const { user, logout } = useAuth()

  return (
    <div className="topbar">
      <div className="brand">
        <div className="brand-icon"><i className="ti ti-scale" /></div>
        <div>
          <div className="brand-name">LexaAI</div>
          <div className="brand-sub">Contract Intelligence</div>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 12, color: "var(--text3)" }}>{user?.email}</span>
        <button
          onClick={logout}
          style={{
            background: "none", border: ".5px solid var(--border)",
            borderRadius: 8, padding: "5px 10px", cursor: "pointer",
            fontSize: 12, color: "var(--text2)", display: "flex",
            alignItems: "center", gap: 5
          }}
        >
          <i className="ti ti-logout" style={{ fontSize: 13 }} />
          Sign out
        </button>
      </div>
    </div>
  )
}