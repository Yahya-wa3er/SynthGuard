import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { UserPlus, Trash2, Shield, User, Eye, EyeOff } from 'lucide-react'

const TEAL = '#00B09B'

export default function AdminUsers() {
  const { getAll, createUser, deleteUser, user: me, isAdmin } = useAuth()

  const [users,    setUsers   ] = useState(getAll())
  const [form,     setForm    ] = useState({ name: '', email: '', password: '', role: 'user', company: '' })
  const [showPwd,  setShowPwd ] = useState(false)
  const [error,    setError   ] = useState('')
  const [success,  setSuccess ] = useState('')

  if (!isAdmin) return (
    <div className="p-8 flex items-center justify-center h-64">
      <p className="text-gray-400 text-sm">Accès réservé à l'administrateur.</p>
    </div>
  )

  const handleCreate = (e) => {
    e.preventDefault()
    setError(''); setSuccess('')
    const result = createUser(form)
    if (!result.ok) { setError(result.error); return }
    setSuccess(`Compte créé pour ${form.name}`)
    setForm({ name: '', email: '', password: '', role: 'user', company: '' })
    setUsers(getAll())
  }

  const handleDelete = (id) => {
    if (id === me.id) { setError("Vous ne pouvez pas supprimer votre propre compte."); return }
    if (!confirm('Supprimer ce compte ?')) return
    deleteUser(id)
    setUsers(getAll())
  }

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  return (
    <div className="p-8 space-y-8 max-w-4xl">
      <div>
        <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: TEAL }}>
          Administration
        </p>
        <h1 className="text-3xl font-bold text-gray-900">Gestion des utilisateurs</h1>
        <p className="text-sm text-gray-400 mt-1">Créez et gérez les accès à SynthGuard Intelligence</p>
      </div>

      {/* Créer un compte */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-5">
          <UserPlus size={16} style={{ color: TEAL }} />
          <h2 className="text-sm font-bold text-gray-800">Créer un nouveau compte</h2>
        </div>

        <form onSubmit={handleCreate} className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1 block">
              Nom complet
            </label>
            <input type="text" required placeholder="Prénom Nom"
              value={form.name} onChange={e => set('name', e.target.value)}
              className="input" />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1 block">
              Email
            </label>
            <input type="email" required placeholder="email@exemple.com"
              value={form.email} onChange={e => set('email', e.target.value)}
              className="input" />
          </div>
          <div className="relative">
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1 block">
              Mot de passe
            </label>
            <div className="relative">
              <input type={showPwd ? 'text' : 'password'} required placeholder="Minimum 8 caractères"
                value={form.password} onChange={e => set('password', e.target.value)}
                className="input pr-10" />
              <button type="button" onClick={() => setShowPwd(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showPwd ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1 block">
              Société
            </label>
            <input type="text" placeholder="Nom de la société (optionnel)"
              value={form.company} onChange={e => set('company', e.target.value)}
              className="input" />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1 block">
              Rôle
            </label>
            <select value={form.role} onChange={e => set('role', e.target.value)} className="input">
              <option value="user">Utilisateur</option>
              <option value="admin">Administrateur</option>
            </select>
          </div>
          <div className="flex items-end">
            <button type="submit"
              className="w-full py-2.5 rounded-xl text-white text-sm font-semibold
                         uppercase tracking-wider transition"
              style={{ background: TEAL }}
              onMouseEnter={e => e.target.style.background = '#008C7A'}
              onMouseLeave={e => e.target.style.background = TEAL}>
              Créer le compte
            </button>
          </div>

          {error && (
            <div className="col-span-2 px-4 py-3 rounded-xl text-sm text-red-600
                            bg-red-50 border border-red-100">{error}</div>
          )}
          {success && (
            <div className="col-span-2 px-4 py-3 rounded-xl text-sm text-green-700
                            bg-green-50 border border-green-100">✓ {success}</div>
          )}
        </form>
      </div>

      {/* Liste des utilisateurs */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-sm font-bold text-gray-800 mb-4">
          Comptes enregistrés ({users.length})
        </h2>
        <div className="space-y-3">
          {users.map(u => (
            <div key={u.id}
                 className="flex items-center justify-between p-4 rounded-xl bg-gray-50
                            border border-gray-100">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full flex items-center justify-center
                                text-sm font-bold text-white"
                     style={{ background: TEAL }}>
                  {u.avatar || u.name?.[0]}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-gray-800">{u.name}</p>
                    {u.role === 'admin' && (
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded-full
                                       text-xs font-semibold"
                            style={{ background: '#E6F7F5', color: TEAL }}>
                        <Shield size={10} /> Admin
                      </span>
                    )}
                    {u.id === me.id && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-gray-200 text-gray-500">
                        Vous
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400">{u.email}
                    {u.company && ` · ${u.company}`}
                  </p>
                </div>
              </div>
              {u.id !== me.id && (
                <button onClick={() => handleDelete(u.id)}
                  className="p-2 rounded-lg text-gray-300 hover:text-red-500
                             hover:bg-red-50 transition">
                  <Trash2 size={15} />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}