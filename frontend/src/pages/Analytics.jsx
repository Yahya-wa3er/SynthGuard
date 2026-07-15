import { useState, useEffect } from 'react'
import { getStats, getHistory } from '../services/api'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Cell, PieChart, Pie,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, Legend
} from 'recharts'
import { TrendingUp, AlertTriangle, Activity, Award } from 'lucide-react'

const MODULE_LABELS = {
  due_diligence   : 'Due Diligence',
  compliance      : 'Compliance & AML',
  credit_risk     : 'Credit Risk',
  audit           : 'Audit Automatisé',
  business_advisor: 'Business Advisor',
}

const SEV_COLORS = {
  normale : '#10b981',
  suspecte: '#f59e0b',
  moderee : '#f97316',
  critique: '#ef4444',
}

const MODULE_COLORS = ['#2563eb','#7c3aed','#0891b2','#059669','#d97706']

// ── Helpers ──────────────────────────────────────────────────────────────────

function buildTimelineData(docs) {
  // Groupe les docs par heure (HH:MM tronqué à l'heure)
  const buckets = {}
  docs.forEach(d => {
    if (!d.detected_at) return
    const dt   = new Date(d.detected_at)
    const key  = `${String(dt.getHours()).padStart(2,'0')}h${String(dt.getMinutes()).padStart(2,'0')}`
    if (!buckets[key]) buckets[key] = { time: key, total: 0, anomalies: 0, normale: 0, suspecte: 0, moderee: 0, critique: 0 }
    buckets[key].total++
    if (d.is_anomaly) buckets[key].anomalies++
    if (d.severity) buckets[key][d.severity] = (buckets[key][d.severity] || 0) + 1
  })
  return Object.values(buckets).slice(-20) // 20 derniers buckets
}

function buildSectorRiskData(docs) {
  const sectors = {}
  docs.forEach(d => {
    if (!d.sector) return
    if (!sectors[d.sector]) sectors[d.sector] = { sector: d.sector, total: 0, anomalies: 0, avgScore: 0, scores: [] }
    sectors[d.sector].total++
    if (d.is_anomaly) sectors[d.sector].anomalies++
    if (d.score != null) sectors[d.sector].scores.push(d.score)
  })
  return Object.values(sectors).map(s => ({
    ...s,
    rate    : s.total > 0 ? +((s.anomalies / s.total) * 100).toFixed(1) : 0,
    avgScore: s.scores.length ? +(s.scores.reduce((a,b) => a+b,0) / s.scores.length).toFixed(5) : 0,
  })).sort((a,b) => b.rate - a.rate)
}

function buildTop10(docs) {
  return [...docs]
    .filter(d => d.is_anomaly)
    .sort((a,b) => (b.score||0) - (a.score||0))
    .slice(0, 10)
}

function buildRadarData(byModule) {
  return Object.entries(byModule).map(([mod, data]) => ({
    module  : MODULE_LABELS[mod] || mod,
    analyses: data.count,
    anomalies: data.anomalies,
    taux    : data.count > 0 ? +((data.anomalies/data.count)*100).toFixed(1) : 0,
  }))
}

// ── Sous-composants ───────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, color = 'blue', Icon }) {
  const colors = {
    blue  : 'bg-blue-50 text-blue-600',
    red   : 'bg-red-50 text-red-500',
    green : 'bg-green-50 text-green-600',
    amber : 'bg-amber-50 text-amber-600',
    purple: 'bg-purple-50 text-purple-600',
  }
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wider">{label}</p>
          <p className="text-2xl font-bold text-gray-800 mt-1">{value ?? '—'}</p>
          {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
        </div>
        {Icon && (
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
            <Icon size={18} />
          </div>
        )}
      </div>
    </div>
  )
}

function SectionTitle({ children }) {
  return (
    <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
      {children}
    </h2>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-100 rounded-lg shadow-lg p-3 text-xs">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>
          {p.name} : {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}
        </p>
      ))}
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function Analytics() {
  const [stats,   setStats  ] = useState(null)
  const [allDocs, setAllDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab,     setTab    ] = useState('overview') // overview | sectors | modules | top10

  useEffect(() => {
    const load = async () => {
      try {
        const [sRes, hRes] = await Promise.all([
          getStats(),
          getHistory({ page: 0, per_page: 200 }),
        ])
        setStats(sRes.data)
        setAllDocs(hRes.data?.docs || [])
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return (
    <div className="p-8 flex items-center justify-center h-64">
      <div className="w-8 h-8 border-4 border-blue-100 border-t-blue-500 rounded-full animate-spin" />
    </div>
  )

  const timelineData  = buildTimelineData(allDocs)
  const sectorData    = buildSectorRiskData(allDocs)
  const top10         = buildTop10(allDocs)
  const radarData     = buildRadarData(stats?.by_module || {})
  const severityData  = Object.entries(stats?.by_severity || {}).map(([k,v]) => ({
    name: k, value: v, color: SEV_COLORS[k] || '#94a3b8'
  }))
  const anomalyRate   = stats?.rate || 0
  const conformRate   = (100 - anomalyRate).toFixed(1)

  const TABS = [
    { id: 'overview', label: 'Vue globale'  },
    { id: 'sectors',  label: 'Par secteur'  },
    { id: 'modules',  label: 'Par module'   },
    { id: 'top10',    label: 'Top risques'  },
  ]

  return (
    <div className="p-8 space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Analytics</h1>
          <p className="text-sm text-gray-400 mt-1">
            Analyse approfondie — {stats?.total?.toLocaleString()} enregistrements
          </p>
        </div>
        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition
                ${tab === t.id
                  ? 'bg-white text-gray-800 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'}`}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPIs globaux — toujours visibles */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard label="Total analysé"    value={stats?.total?.toLocaleString()}
                 Icon={Activity}          color="blue" />
        <KpiCard label="Anomalies"        value={stats?.anomalies?.toLocaleString()}
                 sub={`${anomalyRate}% du total`}
                 Icon={AlertTriangle}     color="red" />
        <KpiCard label="Taux conformité"  value={`${conformRate}%`}
                 Icon={Award}             color="green" />
        <KpiCard label="Score VAE moyen"  value={stats?.avg_score?.toFixed(5)}
                 Icon={TrendingUp}        color="amber" />
      </div>

      {/* ── TAB : Vue globale ─────────────────────────────────────────────── */}
      {tab === 'overview' && (
        <div className="space-y-6">

          {/* Timeline activité */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <SectionTitle>
              <Activity size={14} className="text-blue-500" />
              Timeline des analyses (200 dernières)
            </SectionTitle>
            {timelineData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={timelineData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="time" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Line type="monotone" dataKey="total"    name="Total"
                        stroke="#2563eb" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="anomalies" name="Anomalies"
                        stroke="#ef4444" strokeWidth={2} dot={false} strokeDasharray="4 2" />
                </LineChart>
              </ResponsiveContainer>
            ) : <p className="text-center text-gray-300 text-sm py-16">Aucune donnée</p>}
          </div>

          {/* Distribution sévérités + Répartition anomalies */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
              <SectionTitle>Distribution des sévérités</SectionTitle>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={severityData} dataKey="value" nameKey="name"
                       cx="50%" cy="50%" outerRadius={75} innerRadius={35}
                       label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`}
                       labelLine={false}>
                    {severityData.map((e,i) => <Cell key={i} fill={e.color} />)}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              {/* Légende manuelle */}
              <div className="flex flex-wrap gap-3 mt-2 justify-center">
                {severityData.map((s,i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs text-gray-500">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ background: s.color }} />
                    {s.name} ({s.value.toLocaleString()})
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
              <SectionTitle>Anomalies vs Normaux</SectionTitle>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Normaux',   value: (stats?.total||0) - (stats?.anomalies||0), color: '#10b981' },
                      { name: 'Anomalies', value: stats?.anomalies||0,                       color: '#ef4444' },
                    ]}
                    dataKey="value" nameKey="name"
                    cx="50%" cy="50%" outerRadius={75} innerRadius={35}>
                    {[
                      <Cell key="n" fill="#10b981" />,
                      <Cell key="a" fill="#ef4444" />,
                    ]}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex gap-4 mt-2 justify-center">
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
                  Normaux ({((stats?.total||0)-(stats?.anomalies||0)).toLocaleString()})
                </div>
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                  Anomalies ({(stats?.anomalies||0).toLocaleString()})
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB : Par secteur ─────────────────────────────────────────────── */}
      {tab === 'sectors' && (
        <div className="space-y-6">
          {/* Barres taux d'anomalie par secteur */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <SectionTitle>Taux d'anomalie par secteur (%)</SectionTitle>
            {sectorData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={sectorData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10 }} unit="%" domain={[0,100]} />
                  <YAxis type="category" dataKey="sector" tick={{ fontSize: 11 }} width={90} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="rate" name="Taux anomalie" radius={[0,4,4,0]}>
                    {sectorData.map((s,i) => (
                      <Cell key={i}
                        fill={s.rate > 15 ? '#ef4444' : s.rate > 8 ? '#f97316' : '#10b981'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-center text-gray-300 text-sm py-16">Aucune donnée</p>}
          </div>

          {/* Tableau détaillé */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <SectionTitle>Détail par secteur</SectionTitle>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-400 uppercase tracking-wider border-b border-gray-100">
                  <th className="text-left pb-2">Secteur</th>
                  <th className="text-right pb-2">Total</th>
                  <th className="text-right pb-2">Anomalies</th>
                  <th className="text-right pb-2">Taux</th>
                  <th className="text-right pb-2">Score moy.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {sectorData.map((s,i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="py-2 font-medium text-gray-700 capitalize">{s.sector}</td>
                    <td className="py-2 text-right text-gray-500">{s.total.toLocaleString()}</td>
                    <td className="py-2 text-right text-red-500">{s.anomalies.toLocaleString()}</td>
                    <td className="py-2 text-right">
                      <span className={`font-bold ${s.rate > 15 ? 'text-red-600' : s.rate > 8 ? 'text-orange-500' : 'text-green-600'}`}>
                        {s.rate}%
                      </span>
                    </td>
                    <td className="py-2 text-right font-mono text-gray-500">{s.avgScore}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── TAB : Par module ──────────────────────────────────────────────── */}
      {tab === 'modules' && (
        <div className="space-y-6">
          {/* Radar chart */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <SectionTitle>Comparaison des 5 modules</SectionTitle>
            {radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="module" tick={{ fontSize: 11 }} />
                  <Radar name="Analyses"  dataKey="analyses"  stroke="#2563eb"
                         fill="#2563eb" fillOpacity={0.15} strokeWidth={2} />
                  <Radar name="Anomalies" dataKey="anomalies" stroke="#ef4444"
                         fill="#ef4444" fillOpacity={0.15} strokeWidth={2} />
                  <Legend />
                  <Tooltip content={<CustomTooltip />} />
                </RadarChart>
              </ResponsiveContainer>
            ) : <p className="text-center text-gray-300 text-sm py-16">Aucune donnée</p>}
          </div>

          {/* Barres comparatives */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <SectionTitle>Volume et anomalies par module</SectionTitle>
            {radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={radarData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="module" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar dataKey="analyses"  name="Total"     fill="#2563eb" radius={[3,3,0,0]} />
                  <Bar dataKey="anomalies" name="Anomalies" fill="#ef4444" radius={[3,3,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-center text-gray-300 text-sm py-16">Aucune donnée</p>}
          </div>

          {/* Cards modules */}
          <div className="grid grid-cols-1 xl:grid-cols-5 gap-4">
            {radarData.map((m,i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
                <p className="text-xs text-gray-400 font-medium">{m.module}</p>
                <p className="text-2xl font-bold text-gray-800 mt-1">{m.analyses.toLocaleString()}</p>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-red-500">{m.anomalies} anomalies</span>
                  <span className={`text-xs font-bold ${m.taux > 15 ? 'text-red-600' : m.taux > 8 ? 'text-orange-500' : 'text-green-600'}`}>
                    {m.taux}%
                  </span>
                </div>
                <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-blue-500 transition-all"
                       style={{ width: `${Math.min((m.analyses / (stats?.total||1)) * 100 * 5, 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── TAB : Top 10 risques ──────────────────────────────────────────── */}
      {tab === 'top10' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <SectionTitle>
              <AlertTriangle size={14} className="text-red-500" />
              Top 10 — Scores VAE les plus élevés (anomalies uniquement)
            </SectionTitle>
            {top10.length > 0 ? (
              <>
                {/* Barres horizontales */}
                <div className="space-y-3 mb-6">
                  {top10.map((d,i) => {
                    const pct = Math.min((d.score / (top10[0]?.score || 1)) * 100, 100)
                    const sevC = SEV_COLORS[d.severity] || '#94a3b8'
                    return (
                      <div key={i} className="flex items-center gap-3">
                        <span className="text-xs font-bold text-gray-400 w-4">{i+1}</span>
                        <div className="flex-1">
                          <div className="flex justify-between text-xs mb-1">
                            <span className="font-medium text-gray-700 truncate max-w-[180px]">
                              {d.account}
                            </span>
                            <span className="font-mono text-gray-500 ml-2">
                              {d.score?.toFixed(5)}
                            </span>
                          </div>
                          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div className="h-full rounded-full transition-all"
                                 style={{ width: `${pct}%`, background: sevC }} />
                          </div>
                          <div className="flex gap-2 mt-0.5 text-xs text-gray-400">
                            <span>{d.sector}</span>
                            <span>·</span>
                            <span>{MODULE_LABELS[d.module] || d.module}</span>
                            <span>·</span>
                            <span className="font-medium" style={{ color: sevC }}>
                              {d.severity?.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Tableau détaillé */}
                <table className="w-full text-xs border-t border-gray-100 pt-4">
                  <thead>
                    <tr className="text-gray-400 uppercase tracking-wider border-b border-gray-100">
                      <th className="text-left pb-2">#</th>
                      <th className="text-left pb-2">Compte</th>
                      <th className="text-left pb-2">Secteur</th>
                      <th className="text-left pb-2">Module</th>
                      <th className="text-right pb-2">Score VAE</th>
                      <th className="text-center pb-2">Sévérité</th>
                      <th className="text-left pb-2">Type</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {top10.map((d,i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="py-2 font-bold text-gray-400">{i+1}</td>
                        <td className="py-2 font-medium text-gray-700 max-w-[140px] truncate">{d.account}</td>
                        <td className="py-2 text-gray-400 capitalize">{d.sector}</td>
                        <td className="py-2 text-gray-400">{MODULE_LABELS[d.module] || d.module}</td>
                        <td className="py-2 text-right font-mono font-bold text-red-600">{d.score?.toFixed(5)}</td>
                        <td className="py-2 text-center">
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                                style={{ background: SEV_COLORS[d.severity]+'20', color: SEV_COLORS[d.severity] }}>
                            {d.severity}
                          </span>
                        </td>
                        <td className="py-2 text-gray-400 text-xs">{d.anomaly_label || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : (
              <p className="text-center text-gray-300 text-sm py-16">
                Aucune anomalie dans les 200 derniers enregistrements
              </p>
            )}
          </div>
        </div>
      )}

    </div>
  )
}