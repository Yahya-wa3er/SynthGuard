import { useState } from 'react'
import { compareCompanies } from '../services/api'
import RiskGauge from '../components/RiskGauge'
import { Loader2, ArrowRight } from 'lucide-react'

const SECTORS   = ['technolgy','medical','retail','software','entertainment']
const LOCATIONS = ['United States','United Kingdom','Germany','France','Canada',
                   'Australia','Brazil','India','Kenya','Philippines']
const MODULES   = [
  { value: 'due_diligence',    label: 'Due Diligence'    },
  { value: 'compliance',       label: 'Compliance & AML' },
  { value: 'credit_risk',      label: 'Credit Risk'      },
  { value: 'audit',            label: 'Audit'            },
  { value: 'business_advisor', label: 'Business Advisor' },
]

const emptyForm = () => ({
  account: '', sector: 'technolgy', year_established: 2015,
  revenue: '', employees: '', office_location: 'United States', subsidiary_of: '',
})

export default function Compare() {
  const [formA,   setFormA  ] = useState(emptyForm())
  const [formB,   setFormB  ] = useState(emptyForm())
  const [module,  setModule ] = useState('due_diligence')
  const [result,  setResult ] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError  ] = useState(null)

  const setA = (k, v) => setFormA(f => ({ ...f, [k]: v }))
  const setB = (k, v) => setFormB(f => ({ ...f, [k]: v }))

  const parse = (f) => ({
    ...f,
    year_established: parseInt(f.year_established),
    revenue         : parseFloat(f.revenue),
    employees       : parseInt(f.employees),
    subsidiary_of   : f.subsidiary_of || null,
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true); setError(null); setResult(null)
    try {
      const res = await compareCompanies({
        company_a: parse(formA),
        company_b: parse(formB),
        module,
      })
      setResult(res.data)
    } catch (e) {
      setError(e.response?.data?.error || 'Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-primary">Comparer deux entreprises</h1>
        <p className="text-sm text-gray-400 mt-1">
          Analysez et comparez deux profils côte à côte
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Module selector */}
        <div className="card p-4 mb-6 flex items-center gap-4">
          <span className="text-sm font-medium text-gray-600">Module d'analyse :</span>
          <div className="flex gap-2 flex-wrap">
            {MODULES.map(m => (
              <button
                type="button" key={m.value}
                onClick={() => setModule(m.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition
                  ${module === m.value
                    ? 'bg-accent text-white'
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
          <CompanyForm title="Entreprise A" form={formA} set={setA} color="blue" />
          <CompanyForm title="Entreprise B" form={formB} set={setB} color="indigo" />
        </div>

        <button
          type="submit" disabled={loading}
          className="w-full py-3 bg-primary text-white rounded-lg font-semibold text-sm
                     hover:bg-blue-900 transition disabled:opacity-60 flex items-center justify-center gap-2"
        >
          {loading
            ? <><Loader2 size={15} className="animate-spin" /> Comparaison en cours...</>
            : <><ArrowRight size={15} /> Lancer la comparaison</>
          }
        </button>
      </form>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-lg text-xs text-red-600">
          {error}
        </div>
      )}

      {/* Résultats */}
      {result && (
        <div className="mt-6 space-y-4">
          {/* Recommandation globale */}
          <div className={`card p-4 border-l-4 ${
            result.safer === 'company_a' ? 'border-blue-400' :
            result.safer === 'company_b' ? 'border-indigo-400' : 'border-gray-300'
          }`}>
            <p className="text-sm font-semibold text-gray-700">
              {result.recommendation}
            </p>
          </div>

          {/* Comparaison côte à côte */}
          <div className="grid grid-cols-2 gap-6">
            {[
              { key: 'company_a', label: 'Entreprise A', color: 'blue'   },
              { key: 'company_b', label: 'Entreprise B', color: 'indigo' },
            ].map(({ key, label, color }) => {
              const d = result[key]
              if (!d) return null
              const isSafer = result.safer === key
              const level = d.risk_level?.label?.toLowerCase() === 'critique' ? 'critical'
                          : d.risk_level?.label?.toLowerCase() === 'élevé'    ? 'high'
                          : d.risk_level?.label?.toLowerCase() === 'modéré'   ? 'moderate' : 'low'
              return (
                <div key={key} className={`card p-5 ${isSafer ? 'ring-2 ring-green-200' : ''}`}>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-700">{label}</h3>
                    {isSafer && (
                      <span className="badge badge-low text-xs">✓ Plus sûr</span>
                    )}
                  </div>
                  <p className="text-lg font-bold text-gray-800 mb-1">{d.account}</p>
                  <p className="text-xs text-gray-400 mb-4">{d.sector}</p>
                  <RiskGauge level={level} score={d.score} />
                  {d.anomaly_type && d.anomaly_type !== 'Normal' && (
                    <p className="text-xs text-red-600 mt-3">⚠ {d.anomaly_type}</p>
                  )}
                  {d.interpretation?.verdict && (
                    <p className="text-xs text-gray-500 mt-3 border-t border-gray-100 pt-3">
                      {d.interpretation.verdict}
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function CompanyForm({ title, form, set, color }) {
  const borderColor = color === 'blue' ? 'border-blue-200' : 'border-indigo-200'
  const titleColor  = color === 'blue' ? 'text-blue-600'   : 'text-indigo-600'

  return (
    <div className={`card p-5 border-t-4 ${borderColor}`}>
      <h3 className={`text-sm font-semibold ${titleColor} mb-4`}>{title}</h3>
      <div className="space-y-3">
        <input placeholder="Nom de l'entreprise" required value={form.account}
          onChange={e => set('account', e.target.value)} className="input" />
        <div className="grid grid-cols-2 gap-2">
          <select value={form.sector} onChange={e => set('sector', e.target.value)} className="input">
            {['technolgy','medical','retail','software','entertainment'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <input type="number" placeholder="Année" required value={form.year_established}
            onChange={e => set('year_established', e.target.value)} className="input" />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <input type="number" step="0.01" placeholder="Revenue M$" required
            value={form.revenue} onChange={e => set('revenue', e.target.value)} className="input" />
          <input type="number" placeholder="Employés" required
            value={form.employees} onChange={e => set('employees', e.target.value)} className="input" />
        </div>
        <select value={form.office_location}
          onChange={e => set('office_location', e.target.value)} className="input">
          {['United States','United Kingdom','Germany','France','Canada',
            'Australia','Brazil','India','Kenya','Philippines'].map(l => (
            <option key={l}>{l}</option>
          ))}
        </select>
      </div>
    </div>
  )
}