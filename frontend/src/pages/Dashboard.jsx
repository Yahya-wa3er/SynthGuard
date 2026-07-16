import { useState, useEffect } from 'react'
import { getStats, getHistory } from '../services/api'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, CartesianGrid, Legend,
} from 'recharts'
import {
  Activity, AlertTriangle, TrendingUp, Shield,
  Search, ShieldCheck, CreditCard, ClipboardList, Lightbulb,
  RefreshCw,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

// ── Charte Elavi ─────────────────────────────────────────────────────────────
const TEAL      = '#00B09B'
const TEAL_DARK = '#008C7A'
const TEAL_LITE = '#E6F7F5'

const MODULE_LABELS = {
  due_diligence   : 'Due Diligence',
  compliance      : 'Compliance & AML',
  credit_risk     : 'Credit Risk',
  audit           : 'Audit',
  business_advisor: 'Business Advisor',
}

const MODULE_ICONS = {
  due_diligence   : Search,
  compliance      : ShieldCheck,
  credit_risk     : CreditCard,
  audit           : ClipboardList,
  business_advisor: Lightbulb,
}

const SEV_COLORS = {
  normale : '#10b981',
  suspecte: '#f59e0b',
  moderee : '#f97316',
  critique: '#ef4444',
}

const SEV_LABELS = {
  normale : 'Normale',
  suspecte: 'Suspecte',
  modérée : 'Modérée',
  moderee : 'Modérée',
  critique: 'Critique',
}

// ── Tooltip custom ────────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-lg p-3 text-xs">
      {label && <p className="font-bold text-gray-800 mb-1">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>
          {p.name} : {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}
        </p>
      ))}
    </div>
  )
}

// ── KPI Card ──────────────────────────────────────────────────────────────────
function KpiCard({ label, value, sub, icon: Icon, accent = TEAL }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">{label}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1 leading-none">
            {value ?? '—'}
          </p>
          {sub && <p className="text-xs mt-1.5 font-medium" style={{ color: accent }}>{sub}</p>}
        </div>
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
             style={{ background: accent + '18' }}>
          <Icon size={18} style={{ color: accent }} />
        </div>
      </div>
    </div>
  )
}

// ── Page Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const { user } = useAuth()
  const [stats,   setStats  ] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [tick,    setTick   ] = useState(15)

  const load = async () => {
    try {
      const [sRes, hRes] = await Promise.all([
        getStats(),
        getHistory({ page: 0, per_page: 8 }),
      ])
      setStats(sRes.data)
      setHistory(hRes.data?.docs || [])
      setTick(15)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 15000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const t = setInterval(() => setTick(n => n > 0 ? n - 1 : 15), 1000)
    return () => clearInterval(t)
  }, [])

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="w-10 h-10 rounded-full border-2 border-t-transparent animate-spin mx-auto mb-3"
             style={{ borderColor: TEAL, borderTopColor: 'transparent' }} />
        <p className="text-sm text-gray-400">Chargement...</p>
      </div>
    </div>
  )

  const severityData = Object.entries(stats?.by_severity || {}).map(([k, v]) => ({
    name: SEV_LABELS[k] || k, value: v, color: SEV_COLORS[k] || '#94a3b8',
  }))

  const moduleData = Object.entries(stats?.by_module || {}).map(([k, v]) => ({
    name     : MODULE_LABELS[k] || k,
    total    : v.count,
    anomalies: v.anomalies,
  }))

  const anomalyRate = stats?.rate || 0
  const conformRate = (100 - anomalyRate).toFixed(1)

  return (
    <div className="min-h-screen bg-gray-50 p-8 space-y-7">

      {/* ── Header avec greeting ─────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest mb-2"
             style={{ color: TEAL }}>
            {new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}
          </p>
          <h1 className="text-3xl font-bold text-gray-900">
            Bonjour, <span style={{ color: TEAL }}>
              {user?.name?.split(' ').slice(-1)[0] || 'vous'} !
            </span> 👋
          </h1>
          <p className="text-sm text-gray-400 mt-1.5">
            Voici l'état actuel de votre plateforme SynthGuard Intelligence.
          </p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-xl border
                        border-gray-100 shadow-sm text-xs text-gray-400">
          <RefreshCw size={11} style={{ color: TEAL }} />
          Actualisation dans <span className="font-mono font-bold text-gray-700 ml-1">{tick}s</span>
        </div>
      </div>

      {/* ── KPIs ────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard label="Total analysé"
                 value={stats?.total?.toLocaleString()}
                 accent={TEAL}
                 icon={Activity} />
        <KpiCard label="Anomalies détectées"
                 value={stats?.anomalies?.toLocaleString()}
                 sub={`${anomalyRate}% du total`}
                 accent="#ef4444"
                 icon={AlertTriangle} />
        <KpiCard label="Score VAE moyen"
                 value={stats?.avg_score?.toFixed(5)}
                 accent="#f97316"
                 icon={TrendingUp} />
        <KpiCard label="Taux de conformité"
                 value={`${conformRate}%`}
                 accent="#10b981"
                 icon={Shield} />
      </div>

      {/* ── Charts ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* PieChart sévérités */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <p className="text-sm font-bold text-gray-800 mb-1">Distribution des sévérités</p>
          <p className="text-xs text-gray-400 mb-4">Répartition par niveau de risque</p>
          {severityData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={severityData} dataKey="value" nameKey="name"
                       cx="50%" cy="50%" outerRadius={80} innerRadius={45}
                       paddingAngle={2} strokeWidth={0}>
                    {severityData.map((e, i) => (
                      <Cell key={i} fill={e.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap gap-3 justify-center mt-2">
                {severityData.map((s, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs text-gray-500">
                    <span className="w-2 h-2 rounded-full" style={{ background: s.color }} />
                    {s.name}
                    <span className="font-bold text-gray-800">{s.value.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </>
          ) : <Empty />}
        </div>

        {/* BarChart modules */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <p className="text-sm font-bold text-gray-800 mb-1">Analyses par module</p>
          <p className="text-xs text-gray-400 mb-4">Volume et anomalies détectées</p>
          {moduleData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={moduleData} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#9CA3AF' }}
                       axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }}
                       axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="total"     name="Total"     fill={TEAL}     radius={[4,4,0,0]} />
                <Bar dataKey="anomalies" name="Anomalies" fill="#ef4444"  radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </div>
      </div>

      {/* ── Module cards ────────────────────────────────────────────────── */}
      {Object.keys(stats?.by_module || {}).length > 0 && (
        <div>
          <p className="text-sm font-bold text-gray-800 mb-1">Modules IA</p>
          <p className="text-xs text-gray-400 mb-4">Performance de chaque module d'analyse</p>
          <div className="grid grid-cols-2 xl:grid-cols-5 gap-4">
            {Object.entries(stats.by_module).map(([mod, data]) => {
              const Icon = MODULE_ICONS[mod] || Activity
              const rate = data.count > 0
                ? (data.anomalies / data.count * 100).toFixed(1) : 0
              const pct = Math.min(
                (data.count / (stats?.total || 1)) * 100 * 5, 100
              )
              return (
                <div key={mod}
                     className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                         style={{ background: TEAL_LITE }}>
                      <Icon size={14} style={{ color: TEAL }} />
                    </div>
                    <span className="text-xs font-bold text-red-500">{rate}%</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900">
                    {data.count.toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5 truncate">
                    {MODULE_LABELS[mod]}
                  </p>
                  <div className="mt-3 h-1 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-700"
                         style={{ width: `${pct}%`, background: TEAL }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Alertes + Dernières analyses ────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* Alertes critiques */}
        {stats?.latest_critiques?.length > 0 && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <p className="text-sm font-bold text-gray-800">Alertes critiques récentes</p>
            </div>
            <div className="space-y-3">
              {stats.latest_critiques.map((c, i) => (
                <div key={i}
                     className="flex items-center justify-between p-3 rounded-xl bg-red-50
                                border border-red-100">
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{c.account}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {MODULE_LABELS[c.module] || c.module}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-sm font-bold text-red-600">
                      {c.score?.toFixed(5)}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {c.detected_at
                        ? new Date(c.detected_at).toLocaleTimeString('fr-FR')
                        : '—'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dernières analyses */}
        <div className={`bg-white rounded-2xl border border-gray-100 shadow-sm p-6
                         ${!stats?.latest_critiques?.length ? 'xl:col-span-2' : ''}`}>
          <p className="text-sm font-bold text-gray-800 mb-4">Dernières analyses</p>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-400 uppercase tracking-wider text-left">
                <th className="pb-3 font-semibold">Compte</th>
                <th className="pb-3 font-semibold">Module</th>
                <th className="pb-3 font-semibold">Secteur</th>
                <th className="pb-3 font-semibold text-right">Score VAE</th>
                <th className="pb-3 font-semibold text-center">Sévérité</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h, i) => {
                const sevColor = SEV_COLORS[h.severity] || '#94a3b8'
                return (
                  <tr key={i} className="border-t border-gray-50">
                    <td className="py-2.5 font-semibold text-gray-900 max-w-[130px] truncate">
                      {h.account}
                    </td>
                    <td className="py-2.5 text-gray-400">
                      {MODULE_LABELS[h.module] || '—'}
                    </td>
                    <td className="py-2.5 capitalize text-gray-400">{h.sector}</td>
                    <td className="py-2.5 text-right font-mono font-bold"
                        style={{ color: h.is_anomaly ? '#ef4444' : '#10b981' }}>
                      {h.score?.toFixed(5)}
                    </td>
                    <td className="py-2.5 text-center">
                      <span className="px-2.5 py-1 rounded-full text-xs font-semibold"
                            style={{ background: sevColor + '18', color: sevColor }}>
                        {SEV_LABELS[h.severity] || h.severity}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

const Empty = () => (
  <div className="h-[200px] flex items-center justify-center text-sm text-gray-300">
    Aucune donnée disponible
  </div>
)