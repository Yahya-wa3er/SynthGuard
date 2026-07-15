import { useState } from 'react'
import { Zap, ChevronDown, ChevronUp, Info, Loader2 } from 'lucide-react'
import api from '../services/api'

// Couleur selon le pourcentage de contribution
function contribColor(pct) {
  if (pct >= 40) return { bar: '#ef4444', text: 'text-red-600',   bg: 'bg-red-50',    border: 'border-red-100'    }
  if (pct >= 20) return { bar: '#f97316', text: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-100' }
  if (pct >= 10) return { bar: '#f59e0b', text: 'text-amber-600',  bg: 'bg-amber-50',  border: 'border-amber-100'  }
  return               { bar: '#10b981', text: 'text-green-600',  bg: 'bg-green-50',  border: 'border-green-100'  }
}

export default function ShapExplainer({ docId, score, isAnomaly }) {
  const [open,    setOpen   ] = useState(false)
  const [data,    setData   ] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError  ] = useState(null)

  const load = async () => {
    if (data) { setOpen(o => !o); return }
    setLoading(true); setError(null)
    try {
      const res = await api.post(`/explain/${docId}`)
      setData(res.data)
      setOpen(true)
    } catch (e) {
      setError('Explication non disponible')
    } finally {
      setLoading(false)
    }
  }

  if (!docId) return null

  return (
    <div className="border border-purple-100 rounded-xl overflow-hidden">

      {/* Bouton toggle */}
      <button
        onClick={load}
        className="w-full flex items-center justify-between px-4 py-3
                   bg-purple-50 hover:bg-purple-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-purple-100 flex items-center justify-center">
            <Zap size={12} className="text-purple-600" />
          </div>
          <span className="text-sm font-semibold text-purple-700">
            Explication IA — Contributions par feature
          </span>
          {isAnomaly && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-purple-100 text-purple-600 font-medium">
              SHAP-like
            </span>
          )}
        </div>
        {loading
          ? <Loader2 size={14} className="text-purple-400 animate-spin" />
          : open
            ? <ChevronUp   size={14} className="text-purple-400" />
            : <ChevronDown size={14} className="text-purple-400" />}
      </button>

      {/* Contenu */}
      {open && data && (
        <div className="p-4 space-y-4">

          {/* Explication textuelle */}
          {data.explanation && (
            <div className="flex gap-2 p-3 bg-blue-50 border border-blue-100 rounded-lg">
              <Info size={13} className="text-blue-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-blue-700 leading-relaxed">{data.explanation}</p>
            </div>
          )}

          {/* Barres de contribution */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Top features — contribution au score VAE
            </p>
            <div className="space-y-2.5">
              {data.features.map((f, i) => {
                const c = contribColor(f.contribution)
                return (
                  <div key={i}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-gray-400 w-4">{i + 1}</span>
                        <span className="text-xs font-medium text-gray-700">{f.label}</span>
                      </div>
                      <span className={`text-xs font-bold ${c.text}`}>
                        {f.contribution.toFixed(1)}%
                      </span>
                    </div>
                    {/* Barre de progression */}
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden ml-6">
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${f.contribution}%`, background: c.bar }}
                      />
                    </div>
                    {/* Détail original vs reconstruit */}
                    <div className="flex gap-3 ml-6 mt-1">
                      <span className="text-xs text-gray-400">
                        Original : <span className="font-mono text-gray-600">
                          {f.x_original.toFixed(3)}
                        </span>
                      </span>
                      <span className="text-xs text-gray-400">
                        Reconstruit : <span className="font-mono text-gray-600">
                          {f.x_reconstructed.toFixed(3)}
                        </span>
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Footer méthode */}
          <div className="pt-2 border-t border-gray-100">
            <p className="text-xs text-gray-300 flex items-center gap-1">
              <Zap size={10} />
              Méthode : {data.method} · {data.n_features} features analysées
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="px-4 py-3 text-xs text-red-500 bg-red-50">{error}</div>
      )}
    </div>
  )
}