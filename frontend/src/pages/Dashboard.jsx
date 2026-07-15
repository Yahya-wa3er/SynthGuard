import { useState, useEffect } from 'react'
import { getStats, getHistory } from '../services/api'
import StatsCard from '../components/StatsCard'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts'
import {
  Activity, AlertTriangle, TrendingUp, Shield,
  Search, ShieldCheck, CreditCard, ClipboardList, Lightbulb
} from 'lucide-react'

const MODULE_LABELS = {
  due_diligence   : 'Due Diligence',
  compliance      : 'Compliance',
  credit_risk     : 'Credit Risk',
  audit           : 'Audit',
  business_advisor: 'Business Adv.',
}

const SEVERITY_COLORS = {
  normale : '#10b981',
  suspecte: '#f59e0b',
  moderee : '#f97316',
  critique: '#ef4444',
}

const MODULE_ICONS = {
  due_diligence   : Search,
  compliance      : ShieldCheck,
  credit_risk     : CreditCard,
  audit           : ClipboardList,
  business_advisor: Lightbulb,
}

export default function Dashboard() {
  const [stats,   setStats  ] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const [sRes, hRes] = await Promise.all([
        getStats(),
        getHistory({ page: 0, per_page: 8 }),
      ])
      setStats(sRes.data)
      setHistory(hRes.data.docs || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t) }, [])

  if (loading) return <Loader />

  // Données graphiques
  const severityData = Object.entries(stats?.by_severity || {}).map(([k, v]) => ({
    name: k, value: v, color: SEVERITY_COLORS[k] || '#94a3b8'
  }))

  const moduleData = Object.entries(stats?.by_module || {}).map(([k, v]) => ({
    name: MODULE_LABELS[k] || k,
    total: v.count,
    anomalies: v.anomalies,
  }))

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-primary">Dashboard</h1>
        <p className="text-sm text-gray-400 mt-1">
          Vue globale — mise à jour automatique toutes les 15 secondes
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatsCard
          title="Total analysé"
          value={stats?.total?.toLocaleString()}
          icon={Activity}
          color="blue"
        />
        <StatsCard
          title="Anomalies"
          value={stats?.anomalies?.toLocaleString()}
          subtitle={`${stats?.rate}% du total`}
          icon={AlertTriangle}
          color="red"
        />
        <StatsCard
          title="Score moyen"
          value={stats?.avg_score}
          icon={TrendingUp}
          color="amber"
        />
        <StatsCard
          title="Taux conformité"
          value={`${(100 - (stats?.rate || 0)).toFixed(1)}%`}
          icon={Shield}
          color="green"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* Distribution sévérité */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Distribution des sévérités</h3>
          {severityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={severityData} dataKey="value" nameKey="name"
                     cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) =>
                       `${name} ${(percent * 100).toFixed(0)}%`
                     }>
                  {severityData.map((e, i) => (
                    <Cell key={i} fill={e.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </div>

        {/* Analyses par module */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Analyses par module</h3>
          {moduleData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={moduleData}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="total"    name="Total"     fill="#2563eb" radius={[3,3,0,0]} />
                <Bar dataKey="anomalies" name="Anomalies" fill="#ef4444" radius={[3,3,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </div>
      </div>

      {/* Modules KPIs */}
      {Object.keys(stats?.by_module || {}).length > 0 && (
        <div className="grid grid-cols-2 xl:grid-cols-5 gap-4">
          {Object.entries(stats.by_module).map(([mod, data]) => {
            const Icon = MODULE_ICONS[mod] || Activity
            const rate = data.count > 0 ? (data.anomalies / data.count * 100).toFixed(0) : 0
            return (
              <div key={mod} className="card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Icon size={14} className="text-accent" />
                  <span className="text-xs font-medium text-gray-500">
                    {MODULE_LABELS[mod] || mod}
                  </span>
                </div>
                <p className="text-xl font-bold text-gray-800">{data.count}</p>
                <p className="text-xs text-red-500 mt-0.5">{rate}% anomalies</p>
              </div>
            )
          })}
        </div>
      )}

      {/* Alertes critiques */}
      {stats?.latest_critiques?.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <AlertTriangle size={14} className="text-red-500" />
            Dernières alertes critiques
          </h3>
          <div className="space-y-2">
            {stats.latest_critiques.map((c, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div>
                  <p className="text-sm font-medium text-gray-700">{c.account}</p>
                  <p className="text-xs text-gray-400">{MODULE_LABELS[c.module] || c.module}</p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-xs text-red-600">{c.score?.toFixed(5)}</p>
                  <p className="text-xs text-gray-400">
                    {c.detected_at ? new Date(c.detected_at).toLocaleTimeString('fr-FR') : '—'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Dernières analyses */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Dernières analyses</h3>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-400 uppercase tracking-wider border-b border-gray-100">
              <th className="text-left pb-2">Compte</th>
              <th className="text-left pb-2">Module</th>
              <th className="text-left pb-2">Secteur</th>
              <th className="text-right pb-2">Score</th>
              <th className="text-center pb-2">Sévérité</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {history.map((h, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="py-2 font-medium text-gray-700 max-w-[140px] truncate">{h.account}</td>
                <td className="py-2 text-gray-400">{MODULE_LABELS[h.module] || h.module || '—'}</td>
                <td className="py-2 text-gray-400">{h.sector}</td>
                <td className="py-2 text-right font-mono text-gray-600">{h.score?.toFixed(5)}</td>
                <td className="py-2 text-center">
                  <span className={`badge badge-${h.severity}`}>{h.severity}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const Loader = () => (
  <div className="p-8 flex items-center justify-center h-64">
    <div className="w-8 h-8 border-4 border-blue-100 border-t-accent rounded-full animate-spin" />
  </div>
)

const Empty = () => (
  <div className="h-[220px] flex items-center justify-center text-gray-300 text-sm">
    Aucune donnée disponible
  </div>
)