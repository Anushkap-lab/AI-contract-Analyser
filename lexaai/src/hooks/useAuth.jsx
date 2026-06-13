import { useState, useEffect, useCallback, createContext, useContext } from "react"
import { login as apiLogin, logout as apiLogout, refreshToken } from "../services/api"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]   = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem("access_token"))
  const [loading, setLoading] = useState(true)

  // On mount, try to refresh the token silently (user may have a valid cookie)
  useEffect(() => {
    refreshToken()
      .then(({ access_token }) => {
        setToken(access_token)
        localStorage.setItem("access_token", access_token)
        // Decode user info from token payload
        const payload = JSON.parse(atob(access_token.split(".")[1]))
        setUser({ email: payload.email, id: payload.sub })
      })
      .catch(() => {
        setToken(null)
        localStorage.removeItem("access_token")
      })
      .finally(() => setLoading(false))
  }, [])

  // Auto-refresh every 13 minutes (access token lasts 15 min)
  useEffect(() => {
    if (!token) return
    const interval = setInterval(async () => {
      try {
        const { access_token } = await refreshToken()
        setToken(access_token)
        localStorage.setItem("access_token", access_token)
      } catch {
        setToken(null)
        setUser(null)
        localStorage.removeItem("access_token")
      }
    }, 13 * 60 * 1000)
    return () => clearInterval(interval)
  }, [token])

  const login = async (email, password) => {
    const data = await apiLogin(email, password)
    setToken(data.access_token)
    setUser(data.user)
    localStorage.setItem("access_token", data.access_token)
  }

  const logout = async () => {
    await apiLogout()
    setToken(null)
    setUser(null)
    localStorage.removeItem("access_token")
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)