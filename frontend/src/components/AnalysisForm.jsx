import { useState, useEffect } from 'react'
import { getSectorBenchmark } from '../services/api'
import { Loader2, Play, ChevronDown, ChevronUp, Sparkles } from 'lucide-react'

const SECTORS   = ['technolgy','medical','retail','software','entertainment']
const LOCATIONS = ['United States','United Kingdom','Germany','France','Canada',
                   'Australia','Brazil','India','Kenya','Philippines']

const SECTOR_LABELS = {
  technolgy: 'Technology', medical: 'Medical', retail: 'Retail',
  software: 'Software', entertainment: 'Entertainment',
}

// ── Cas de démonstration ──────────────────────────────────────────────────────
const DEMO_CASES = [
  {
    id      : 'normal',
    label   : 'Profil Normal',
    tag     : 'LOW RISK',
    tagColor: '#10b981',
    desc    : 'Entreprise saine, conforme aux benchmarks sectoriels',
    icon    : '✅',
    data    : {
      account         : 'Vertex Technologies Inc.',
      sector          : 'technolgy',
      year_established: 2010,
      revenue         : 1200,
      employees       : 450,
      office_location : 'United States',
      subsidiary_of   : '',
    },
  },
  {
    id      : 'type1',
    label   : 'Coquille Vide',
    tag     : 'CRITIQUE',
    tagColor: '#ef4444',
    desc    : 'Société créée en 2025, 2 employés, revenue 25 000 M$',
    icon    : '🔴',
    data    : {
      account         : 'Shell Corp T1 Demo',
      sector          : 'software',
      year_established: 2025,
      revenue         : 25000,
      employees       : 2,
      office_location : 'Kenya',
      subsidiary_of   : '',
    },
  },
  {
    id      : 'type3',
    label   : 'Filiale Fantôme',
    tag     : 'SUSPECT',
    tagColor: '#f97316',
    desc    : 'Filiale avec 1 employé et revenue quasi-nul (0.05 M$)',
    icon    : '🟠',
    data    : {
      account         : 'Phantom Sub Demo',
      sector          : 'retail',
      year_established: 2018,
      revenue         : 0.05,
      employees       : 1,
      office_location : 'Philippines',
      subsidiary_of   : 'Offshore Holdings LLC',
    },
  },
  {
    id      : 'type2',
    label   : 'Outlier Sectoriel',
    tag     : 'MODÉRÉ',
    tagColor: '#f59e0b',
    desc    : 'Entertainment avec revenue 95 000 M$ — impossible pour ce secteur',
    icon    : '🟡',
    data    : {
      account         : 'Mega Entertainment Demo',
      sector          : 'entertainment',
      year_established: 2005,
      revenue         : 95000,
      employees       : 35000,
      office_location : 'United States',
      subsidiary_of   : '',
    },
  },
]

// ── Composant principal ───────────────────────────────────────────────────────
export default function AnalysisForm({ onSubmit, loading, extraFields = [] }) {
  const [form, setForm] = useState({
    account         : '',
    sector          : 'technolgy',
    year_established: 2015,
    revenue         : '',
    employees       : '',
    office_location : 'United States',
    subsidiary_of   : '',
  })
  const [benchmark,    setBenchmark   ] = useState(null)
  const [showDemo,     setShowDemo    ] = useState(false)
  const [activeDemo,   setActiveDemo  ] = useState(null)
  const [demoFlash,    setDemoFlash   ] = useState(false)

  // Charger le benchmark quand le secteur change
  useEffect(() => {
    getSectorBenchmark(form.sector)
      .then(r => setBenchmark(r.data.benchmark))
      .catch(() => setBenchmark(null))
  }, [form.sector])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  // Pré-remplir avec un cas démo
  const applyDemo = (demo) => {
    setActiveDemo(demo.id)
    setForm(demo.data)
    setDemoFlash(true)
    setShowDemo(false)
    setTimeout(() => setDemoFlash(false), 800)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({
      ...form,
      year_established: parseInt(form.year_established),
      revenue         : parseFloat(form.revenue),
      employees       : parseInt(form.employees),
      subsidiary_of   : form.subsidiary_of || null,
    })
  }

  const activeDemoCase = DEMO_CASES.find(d => d.id === activeDemo)

  return (
    <form onSubmit={handleSubmit} className="space-y-4">

      {/* ── Bouton Mode Démo ───────────────────────────────────────────── */}
      <div className="relative" style={{ zIndex: 40 }}>
        <button
          type="button"
          onClick={() => setShowDemo(v => !v)}
          className="w-full flex items-center justify-between px-4 py-2.5 rounded-xl
                     border transition-all text-sm font-medium"
          style={{
            background   : showDemo ? '#eff6ff' : '#f8faff',
            border       : `1.5px solid ${showDemo ? '#2563eb' : '#dbeafe'}`,
            color        : '#2563eb',
          }}
        >
          <span className="flex items-center gap-2">
            <Sparkles size={14} />
            Mode démonstration
            {activeDemoCase && (
              <span className="px-2 py-0.5 rounded-full text-xs font-bold"
                    style={{ background: activeDemoCase.tagColor + '20',
                             color: activeDemoCase.tagColor }}>
                {activeDemoCase.icon} {activeDemoCase.label}
              </span>
            )}
          </span>
          {showDemo
            ? <ChevronUp size={14} />
            : <ChevronDown size={14} />}
        </button>

        {/* Dropdown des cas */}
        {showDemo && (
          <div className="absolute top-full left-0 right-0 z-50 mt-1 rounded-xl shadow-xl
                          border border-blue-100 overflow-hidden"
               style={{ background: '#fff', maxHeight: '320px', overflowY: 'auto' }}>
            <div className="p-3 border-b border-gray-100">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Sélectionner un scénario de test
              </p>
            </div>
            {DEMO_CASES.map(demo => (
              <button
                key={demo.id}
                type="button"
                onClick={() => applyDemo(demo)}
                className="w-full flex items-start gap-3 px-4 py-3 text-left
                           hover:bg-gray-50 transition-colors border-b border-gray-50
                           last:border-0"
              >
                <span className="text-lg flex-shrink-0 mt-0.5">{demo.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-800">
                      {demo.label}
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-xs font-bold"
                          style={{ background: demo.tagColor + '18',
                                   color: demo.tagColor }}>
                      {demo.tag}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5 truncate">{demo.desc}</p>
                </div>
                <Play size={13} className="text-blue-400 flex-shrink-0 mt-1" />
              </button>
            ))}
            <div className="px-4 py-2 bg-blue-50">
              <p className="text-xs text-blue-500">
                💡 Les données sont pré-remplies — cliquez sur "Lancer l'analyse IA"
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Flash de confirmation quand démo appliquée */}
      {demoFlash && (
        <div className="p-2 rounded-lg text-center text-xs font-medium animate-pulse"
             style={{ background: '#eff6ff', color: '#2563eb' }}>
          ✓ Données pré-remplies — lancez l'analyse
        </div>
      )}

      {/* ── Champs du formulaire ───────────────────────────────────────── */}

      {/* Compte */}
      <Field label="Nom de l'entreprise">
        <input
          type="text" required placeholder="ex: Acme Corporation"
          value={form.account} onChange={e => set('account', e.target.value)}
          className="input"
        />
      </Field>

      {/* Secteur + Localisation */}
      <div className="grid grid-cols-2 gap-3">
        <Field label="Secteur d'activité">
          <select value={form.sector}
                  onChange={e => set('sector', e.target.value)}
                  className="input">
            {SECTORS.map(s => (
              <option key={s} value={s}>{SECTOR_LABELS[s]}</option>
            ))}
          </select>
        </Field>
        <Field label="Localisation">
          <select value={form.office_location}
                  onChange={e => set('office_location', e.target.value)}
                  className="input">
            {LOCATIONS.map(l => <option key={l}>{l}</option>)}
          </select>
        </Field>
      </div>

      {/* Année + Revenue + Employés */}
      <div className="grid grid-cols-3 gap-3">
        <Field label="Année création">
          <input
            type="number" required min="1900" max="2030"
            placeholder="2015"
            value={form.year_established}
            onChange={e => set('year_established', e.target.value)}
            className="input"
          />
        </Field>
        <Field label="Revenue (M$)"
               hint={benchmark ? `Moy: ${benchmark.avg_revenue?.toLocaleString()}` : null}>
          <input
            type="number" required step="0.01" min="0"
            placeholder={benchmark ? benchmark.avg_revenue : '1500'}
            value={form.revenue}
            onChange={e => set('revenue', e.target.value)}
            className="input"
          />
        </Field>
        <Field label="Employés"
               hint={benchmark ? `Moy: ${benchmark.avg_employees?.toLocaleString()}` : null}>
          <input
            type="number" required min="0"
            placeholder={benchmark ? benchmark.avg_employees : '250'}
            value={form.employees}
            onChange={e => set('employees', e.target.value)}
            className="input"
          />
        </Field>
      </div>

      {/* Filiale */}
      <Field label="Filiale de (optionnel)">
        <input
          type="text" placeholder="Laisser vide si entité indépendante"
          value={form.subsidiary_of}
          onChange={e => set('subsidiary_of', e.target.value)}
          className="input"
        />
      </Field>

      {/* Champs supplémentaires */}
      {extraFields.map(({ name, label, type = 'text', placeholder }) => (
        <Field key={name} label={label}>
          <input
            type={type} placeholder={placeholder}
            value={form[name] || ''}
            onChange={e => set(name, e.target.value)}
            className="input"
          />
        </Field>
      ))}

      {/* Benchmark hint */}
      {benchmark && (
        <div className="p-3 bg-blue-50 border border-blue-100 rounded-lg">
          <p className="text-xs text-blue-600 font-medium mb-1">
            Référence secteur {SECTOR_LABELS[form.sector]}
          </p>
          <div className="grid grid-cols-3 gap-2 text-xs text-blue-500">
            <span>Revenue min: ${benchmark.min_revenue?.toLocaleString()}M</span>
            <span>Employés min: {benchmark.min_employees}</span>
            <span>Risque: {benchmark.risk_profile}</span>
          </div>
        </div>
      )}

      {/* Submit */}
      <button
        type="submit" disabled={loading}
        className="w-full py-3 bg-primary text-white rounded-lg font-semibold text-sm
                   hover:bg-primary-dark transition disabled:opacity-60
                   flex items-center justify-center gap-2"
      >
        {loading ? (
          <><Loader2 size={15} className="animate-spin" /> Analyse en cours...</>
        ) : activeDemo ? (
          <><Play size={15} /> Lancer la démo — {activeDemoCase?.label}</>
        ) : (
          'Lancer l\'analyse IA'
        )}
      </button>
    </form>
  )
}

function Field({ label, hint, children }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs font-medium text-gray-600 uppercase tracking-wider">
          {label}
        </label>
        {hint && <span className="text-xs text-gray-400">{hint}</span>}
      </div>
      {children}
    </div>
  )
}