import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Eye, EyeOff, Loader2, ShieldCheck } from 'lucide-react'
import loginBg from '../assets/login-bg.jpg'

const TEAL = '#00B09B'

export default function Login() {
  const { login } = useAuth()
  const navigate  = useNavigate()

  const [email,    setEmail   ] = useState('')
  const [password, setPassword] = useState('')
  const [showPwd,  setShowPwd ] = useState(false)
  const [error,    setError   ] = useState('')
  const [loading,  setLoading ] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    await new Promise(r => setTimeout(r, 600)) // délai UX
    const result = login(email, password)
    setLoading(false)
    if (result.ok) {
      navigate('/')
    } else {
      setError(result.error)
    }
  }

  return (
    <div className="min-h-screen flex" style={{ background: '#F9FAFB' }}>

      {/* ── Panel gauche — branding ──────────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative overflow-hidden"
           style={{
             backgroundImage   : `url(${loginBg})`,
             backgroundSize    : '110%',
             backgroundPosition: '50% 20%',
             backgroundRepeat  : 'no-repeat',
             backgroundColor  : '#f5f0eb',
           }}>

        {/* Overlay minimal — photo bien visible */}
        <div className="absolute inset-0"
             style={{ background: 'linear-gradient(180deg, rgba(0,0,0,0.25) 0%, rgba(0,176,155,0.45) 100%)' }} />

        {/* Logo */}
        <div className="flex items-center gap-3 relative z-10">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
               style={{ background: TEAL }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                    stroke="white" strokeWidth="2.5"
                    strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <p className="font-bold text-white text-lg leading-tight">SynthGuard</p>
            <p className="text-xs leading-tight" style={{ color: TEAL }}>Intelligence v2.0</p>
          </div>
        </div>

        {/* Tagline avec fond semi-transparent pour lisibilité */}
        <div className="relative z-10 p-6 rounded-2xl"
             style={{ background: 'rgba(0,0,0,0.35)', backdropFilter: 'blur(8px)' }}>
          <h2 className="text-4xl font-bold text-white leading-tight mb-4">
            Analysez vos<br />
            prospects B2B<br />
            <span style={{ color: '#2DDCC8' }}>en quelques secondes.</span>
          </h2>
          <p className="text-sm leading-relaxed max-w-sm" style={{ color: 'rgba(255,255,255,0.75)' }}>
            Avant que ça coûte cher. Moteur Beta-VAE · AUC 0.9999 · Recall 100%
          </p>

          {/* Stats */}
          <div className="flex gap-8 mt-6 pt-6"
               style={{ borderTop: '1px solid rgba(255,255,255,0.15)' }}>
            {[
              { label: 'Analyses', value: '249K+' },
              { label: 'Précision', value: '99.9%' },
              { label: 'Modules IA', value: '5' },
            ].map((s, i) => (
              <div key={i}>
                <p className="text-2xl font-bold text-white">{s.value}</p>
                <p className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.5)' }}>{s.label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <p className="text-xs text-gray-600 relative z-10">
          © 2026 SynthGuard Intelligence · ENSA Fès 
        </p>
      </div>

      {/* ── Panel droit — formulaire ─────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">

          {/* Header mobile */}
          <div className="flex items-center gap-3 mb-10 lg:hidden">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                 style={{ background: TEAL }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                      stroke="white" strokeWidth="2.5"
                      strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <p className="font-bold text-gray-900">SynthGuard Intelligence</p>
          </div>

          {/* Titre */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Connexion</h1>
            <p className="text-sm text-gray-400 mt-1">
              Accédez à votre espace d'analyse IA
            </p>
          </div>

          {/* Formulaire */}
          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Email */}
            <div>
              <label className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1.5 block">
                Adresse email
              </label>
              <input
                type="email" required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="vous@exemple.com"
                className="w-full px-4 py-3 text-sm border border-gray-200 rounded-xl
                           bg-white placeholder-gray-300 transition
                           focus:outline-none focus:border-teal-500 focus:ring-2"
                style={{ '--tw-ring-color': '#B2E8E2' }}
              />
            </div>

            {/* Mot de passe */}
            <div>
              <label className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1.5 block">
                Mot de passe
              </label>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'} required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-3 pr-12 text-sm border border-gray-200 rounded-xl
                             bg-white placeholder-gray-300 transition
                             focus:outline-none focus:border-teal-500 focus:ring-2"
                />
                <button type="button"
                  onClick={() => setShowPwd(v => !v)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400
                             hover:text-gray-600 transition">
                  {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Erreur */}
            {error && (
              <div className="px-4 py-3 rounded-xl text-sm text-red-600
                              bg-red-50 border border-red-100">
                {error}
              </div>
            )}

            {/* Bouton */}
            <button
              type="submit" disabled={loading}
              className="w-full py-3.5 rounded-xl text-white font-semibold text-sm
                         uppercase tracking-wider transition
                         disabled:opacity-60 flex items-center justify-center gap-2"
              style={{ background: loading ? '#9CA3AF' : TEAL }}
              onMouseEnter={e => !loading && (e.target.style.background = '#008C7A')}
              onMouseLeave={e => !loading && (e.target.style.background = TEAL)}
            >
              {loading
                ? <><Loader2 size={16} className="animate-spin" /> Connexion...</>
                : 'Se connecter'}
            </button>
          </form>

          {/* Info compte */}
          <div className="mt-8 p-4 rounded-xl border border-gray-100 bg-white">
            <div className="flex items-start gap-3">
              <ShieldCheck size={16} style={{ color: TEAL }} className="flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-gray-700">Accès sur invitation</p>
                <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">
                  Les comptes sont créés par l'administrateur.
                  Contactez votre responsable pour obtenir un accès.
                </p>
              </div>
            </div>
          </div>

          <p className="text-xs text-gray-300 text-center mt-6">
            SynthGuard Intelligence v2.0 · ENSA Fès 2026
          </p>
        </div>
      </div>
    </div>
  )
}