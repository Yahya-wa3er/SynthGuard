import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

// ── Clé secrète JWT (simulé côté frontend) ───────────────────────────────────
const JWT_SECRET = 'synthguard_secret_2026'

// ── Utilitaires JWT simulé ────────────────────────────────────────────────────
function base64url(str) {
  return btoa(unescape(encodeURIComponent(str)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function createToken(payload) {
  const header  = base64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body    = base64url(JSON.stringify({ ...payload, iat: Date.now() }))
  const sig     = base64url(`${header}.${body}.${JWT_SECRET}`)
  return `${header}.${body}.${sig}`
}

function parseToken(token) {
  try {
    const [, body] = token.split('.')
    return JSON.parse(decodeURIComponent(escape(atob(
      body.replace(/-/g, '+').replace(/_/g, '/')
    ))))
  } catch { return null }
}

// ── Utilisateurs par défaut (admin pré-créé) ─────────────────────────────────
const DEFAULT_USERS = [
  {
    id      : '1',
    email   : 'yahya@synthguard.ai',
    password: 'SynthGuard2026!',
    name    : 'El Houti Yahya',
    role    : 'admin',
    avatar  : 'YH',
    company : 'ENSA Fès',
  },
]

function getUsers() {
  const stored = localStorage.getItem('sg_users')
  if (stored) return JSON.parse(stored)
  localStorage.setItem('sg_users', JSON.stringify(DEFAULT_USERS))
  return DEFAULT_USERS
}

function saveUsers(users) {
  localStorage.setItem('sg_users', JSON.stringify(users))
}

// ── Provider ──────────────────────────────────────────────────────────────────
export function AuthProvider({ children }) {
  const [user,    setUser   ] = useState(null)
  const [loading, setLoading] = useState(true)

  // Restaurer la session au montage
  useEffect(() => {
    const token = localStorage.getItem('sg_token')
    if (token) {
      const payload = parseToken(token)
      if (payload) {
        const users = getUsers()
        const found = users.find(u => u.id === payload.id)
        if (found) setUser(found)
      }
    }
    setLoading(false)
  }, [])

  // Connexion
  const login = (email, password) => {
    const users = getUsers()
    const found = users.find(
      u => u.email.toLowerCase() === email.toLowerCase() && u.password === password
    )
    if (!found) return { ok: false, error: 'Email ou mot de passe incorrect' }
    const token = createToken({ id: found.id, email: found.email, role: found.role })
    localStorage.setItem('sg_token', token)
    setUser(found)
    return { ok: true }
  }

  // Déconnexion
  const logout = () => {
    localStorage.removeItem('sg_token')
    setUser(null)
  }

  // Créer un compte (admin only)
  const createUser = (newUser) => {
    const users = getUsers()
    if (users.find(u => u.email.toLowerCase() === newUser.email.toLowerCase())) {
      return { ok: false, error: 'Cet email est déjà utilisé' }
    }
    const user = {
      id      : Date.now().toString(),
      ...newUser,
      role    : newUser.role || 'user',
      avatar  : newUser.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase(),
    }
    saveUsers([...users, user])
    return { ok: true, user }
  }

  // Supprimer un compte (admin only)
  const deleteUser = (id) => {
    const users = getUsers().filter(u => u.id !== id)
    saveUsers(users)
  }

  // Lister les utilisateurs (admin only)
  const getAll = () => getUsers()

  return (
    <AuthContext.Provider value={{
      user, loading, login, logout, createUser, deleteUser, getAll,
      isAdmin: user?.role === 'admin',
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)