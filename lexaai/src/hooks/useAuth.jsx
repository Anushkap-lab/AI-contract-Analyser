import { useState, useEffect, createContext, useContext } from "react"
import { login as apiLogin, logout as apiLogout, refreshToken } from "../services/api"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {

  const [user, setUser]       = useState(null)
  const [token, setToken]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    refreshToken()
      .then(({ access_token }) => {
        const payload = JSON.parse(atob(access_token.split(".")[1]))
        setToken(access_token)
        setUser({ id: payload.sub, email: payload.email })
        localStorage.setItem("access_token", access_token)
      })
      .catch(() => {
        setToken(null)
        setUser(null)
        localStorage.removeItem("access_token")
      })
      .finally(() => setLoading(false))
  }, [])

 
  useEffect(() => {
    if (!token) return
    const interval = setInterval(async () => {
      try {
        const { access_token } = await refreshToken()
        const payload = JSON.parse(atob(access_token.split(".")[1]))
        setToken(access_token)
        setUser({ id: payload.sub, email: payload.email })
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
    try {
      await apiLogout()
    } finally {
      localStorage.removeItem("access_token")
      window.location.href = "/"
    }
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)