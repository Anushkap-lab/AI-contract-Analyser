import { useAuth } from "../hooks/useAuth.jsx"
import AuthPage from "./AuthPage"

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="spin" style={{ margin: "40vh auto", width: 28, height: 28, border: "2px solid var(--gold)", borderTopColor: "transparent", borderRadius: "50%" }} />
  if (!user) return <AuthPage />
  return children
}