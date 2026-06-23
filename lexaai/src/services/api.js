const BASE = import.meta.env.VITE_API_URL

export async function register(email, password, fullName) {
  const res = await fetch(`${BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || "Registration failed")
  }
  return res.json()
}

export async function login(email, password) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",   // ← needed for the httpOnly cookie
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || "Login failed")
  }
  return res.json()  // { access_token, user }
}

export async function logout() {
  await fetch(`${BASE}/auth/logout`, {
    method: "POST",
    credentials: "include",
  })
}

export async function refreshToken() {
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    credentials: "include",
  })
  if (!res.ok) throw new Error("Session expired")
  return res.json()  // { access_token }
}
function authHeaders() {
  const token = localStorage.getItem("access_token")
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function analyseContract(file) {
  const form = new FormData()
  form.append("file", file)

  const res = await fetch(`${BASE}/upload`, {
    method: "POST",
    headers: { ...authHeaders() },  
    credentials: "include",
    body: form,
  })

  if (res.status === 401) {
    window.location.reload()  
    return
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Server error ${res.status}`)
  }
  return res.json()
}

export async function askQuestion(question, contractId) {
  const res = await fetch(`${BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify({ question, contract_id: contractId }),
  })
  if (!res.ok) throw new Error("Question failed")
  const data = await res.json()
  return data.answer
}