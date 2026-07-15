import { useState, useEffect } from 'react'
import { getHistory, downloadPDF } from '../services/api'
import { Download, Filter, RefreshCw } from 'lucide-react'

const MODULE_LABELS = {
  due_diligence   : 'Due Diligence',
  compliance      : 'Compliance & AML',
  credit_risk     : 'Credit Risk',
  audit           : 'Audit',
  business_advisor: 'Business Advisor',
}

const TYPE_LABELS = {
  0: '—',
  1: 'Coquille vide',
  2: 'Outlier sectoriel',
  3: 'Filiale fantôme',
  4: 'Saisie aberrante',
}

export default function History() {
  const [docs,      setDocs     ] = useState([])
  const [total,     setTotal    ] = useState(0)
  const [page,      setPage     ] = useState(0)
  const [loading,   setLoading  ] = useState(true)
  const [module,    setModule   ] = useState('')
  const [severity,  setSeverity ] = useState('')
  const [isAnomaly, setIsAnomaly] = useState('')

  const PER_PAGE = 20

  const load = async () => {
    setLoading(true)
    try {
      const res = await getHistory({
        page,
        per_page: PER_PAGE,
        ...(module    && { module }),
        ...(severity  && { severity }),
        ...(isAnomaly && { is_anomaly: isAnomaly }),
      })
      setDocs(res.data.docs || [])
      setTotal(res.data.total || 0)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, module, severity, isAnomaly])

  const totalPages = Math.ceil(total / PER_PAGE)

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-primary">Historique des analyses</h1>
          <p className="text-sm text-gray-400 mt-1">
            {total.toLocaleString()} enregistrements au total
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 px-4 py-2 text-sm border border-gray-200
                     rounded-lg text-gray-500 hover:bg-gray-50 transition"
        >
          <RefreshCw size={14} /> Actualiser
        </button>
      </div>

      {/* Filtres */}
      <div className="card p-4 mb-5 flex flex-wrap items-center gap-3">
        <Filter size={14} className="text-gray-400" />
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
          Filtres
        </span>

        <select
          value={module} onChange={e => { setModule(e.target.value); setPage(0) }}
          className="input text-xs py-1.5 w-40"
        >
          <option value="">Tous les modules</option>
          {Object.entries(MODULE_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>

        <select
          value={severity} onChange={e => { setSeverity(e.target.value); setPage(0) }}
          className="input text-xs py-1.5 w-36"
        >
          <option value="">Toutes sévérités</option>
          <option value="normale">Normale</option>
          <option value="suspecte">Suspecte</option>
          <option value="moderee">Modérée</option>
          <option value="critique">Critique</option>
        </select>

        <select
          value={isAnomaly} onChange={e => { setIsAnomaly(e.target.value); setPage(0) }}
          className="input text-xs py-1.5 w-36"
        >
          <option value="">Tous statuts</option>
          <option value="true">Anomalies</option>
          <option value="false">Normaux</option>
        </select>

        {(module || severity || isAnomaly) && (
          <button
            onClick={() => { setModule(''); setSeverity(''); setIsAnomaly(''); setPage(0) }}
            className="text-xs text-accent hover:underline"
          >
            Effacer les filtres
          </button>
        )}
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr className="text-gray-400 uppercase tracking-wider">
                <th className="text-left px-4 py-3">Compte</th>
                <th className="text-left px-4 py-3">Module</th>
                <th className="text-left px-4 py-3">Secteur</th>
                <th className="text-right px-4 py-3">Revenue</th>
                <th className="text-right px-4 py-3">Employés</th>
                <th className="text-right px-4 py-3">Score VAE</th>
                <th className="text-center px-4 py-3">Sévérité</th>
                <th className="text-center px-4 py-3">Type</th>
                <th className="text-left px-4 py-3">Date</th>
                <th className="text-center px-4 py-3">PDF</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading ? (
                <tr>
                  <td colSpan="10" className="py-12 text-center">
                    <div className="w-6 h-6 border-4 border-blue-100 border-t-accent
                                    rounded-full animate-spin mx-auto" />
                  </td>
                </tr>
              ) : docs.length === 0 ? (
                <tr>
                  <td colSpan="10" className="py-12 text-center text-gray-300">
                    Aucun enregistrement trouvé
                  </td>
                </tr>
              ) : docs.map((d, i) => (
                <tr key={i} className="hover:bg-gray-50 transition">
                  <td className="px-4 py-3 font-medium text-gray-700 max-w-[130px] truncate">
                    {d.account || '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {MODULE_LABELS[d.module] || d.module || '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-400">{d.sector || '—'}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-600">
                    {d.revenue ? Number(d.revenue).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600">
                    {d.employees ? Number(d.employees).toLocaleString() : '—'}
                  </td>
                  <td className={`px-4 py-3 text-right font-mono font-medium
                    ${d.is_anomaly ? 'text-red-500' : 'text-green-500'}`}>
                    {d.score?.toFixed(6) || '—'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`badge badge-${d.severity}`}>
                      {d.severity || '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-gray-400">
                    {TYPE_LABELS[d.predicted_type] || '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {d.detected_at
                      ? new Date(d.detected_at).toLocaleString('fr-FR', {
                          day: '2-digit', month: '2-digit', year: '2-digit',
                          hour: '2-digit', minute: '2-digit',
                        })
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {d.id && (
                      <button
                        onClick={() => downloadPDF(d.id)}
                        className="p-1.5 text-gray-400 hover:text-accent
                                   hover:bg-blue-50 rounded transition"
                        title="Télécharger le rapport PDF"
                      >
                        <Download size={13} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
            <p className="text-xs text-gray-400">
              Page {page + 1} sur {totalPages} —{' '}
              {total.toLocaleString()} résultats
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg
                           text-gray-500 hover:bg-gray-50 disabled:opacity-40 transition"
              >
                ← Précédent
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg
                           text-gray-500 hover:bg-gray-50 disabled:opacity-40 transition"
              >
                Suivant →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}