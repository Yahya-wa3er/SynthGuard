import { useEffect, useState } from 'react'
import Shapexplainer from './Shapexplainer.jsx'
import RiskGauge from './RiskGauge'
import { downloadPDF } from '../services/api'
import { Download, AlertTriangle, CheckCircle, Info, TrendingUp,
         Shield, CreditCard, ClipboardList, Lightbulb } from 'lucide-react'

const MODULE_LABELS = {
  due_diligence   : 'Due Diligence',
  compliance      : 'Compliance & AML',
  credit_risk     : 'Credit Risk',
  audit           : 'Audit Automatisé',
  business_advisor: 'Business Advisor',
}

const MODULE_ICONS = {
  due_diligence   : Shield,
  compliance      : AlertTriangle,
  credit_risk     : CreditCard,
  audit           : ClipboardList,
  business_advisor: Lightbulb,
}

const SEVERITY_CONFIG = {
  critique: { bg: 'bg-red-50',    border: 'border-red-200',    text: 'text-red-700',
               badge: 'bg-red-100 text-red-700',    dot: 'bg-red-500',    label: 'CRITIQUE' },
  moderee : { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700',
               badge: 'bg-orange-100 text-orange-700', dot: 'bg-orange-500', label: 'MODÉRÉE' },
  suspecte: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700',
               badge: 'bg-yellow-100 text-yellow-700', dot: 'bg-yellow-500', label: 'SUSPECTE' },
  normale : { bg: 'bg-green-50',  border: 'border-green-200',  text: 'text-green-700',
               badge: 'bg-green-100 text-green-700',  dot: 'bg-green-500',  label: 'NORMALE' },
}

// Barre de score animée
function AnimatedScore({ score }) {
  const [displayed, setDisplayed] = useState(0)
  const max = 0.5 // au-delà de 0.5 c'est clairement anomalie
  const pct = Math.min((score / max) * 100, 100)

  useEffect(() => {
    let start = null
    const duration = 800
    const animate = (ts) => {
      if (!start) start = ts
      const progress = Math.min((ts - start) / duration, 1)
      setDisplayed(score * progress)
      if (progress < 1) requestAnimationFrame(animate)
    }
    requestAnimationFrame(animate)
  }, [score])

  const color = score >= 0.06 ? '#ef4444'
              : score >= 0.04 ? '#f97316'
              : score >= 0.02 ? '#f59e0b'
              : '#10b981'

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-xs text-gray-500 font-medium">Score VAE</span>
        <span className="text-sm font-bold font-mono" style={{ color }}>
          {displayed.toFixed(6)}
        </span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-800 ease-out"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <div className="flex justify-between text-xs text-gray-300">
        <span>Normal</span>
        <span>Seuil τ=0.020</span>
        <span>Critique</span>
      </div>
    </div>
  )
}

// Métriques spécifiques par module
function MetricGrid({ result }) {
  const {
    aml_score, debt_ratio, repayment_capacity, credit_limit_est,
    audit_score, viability_score, action, recommended_sector, n_findings,
  } = result

  const metrics = [
    aml_score       !== undefined && { label: 'Score AML',        value: `${aml_score}/100`,                 color: aml_score > 50 ? 'text-red-600' : 'text-green-600' },
    debt_ratio      !== undefined && { label: 'Ratio dette',       value: `${debt_ratio}%`,                   color: debt_ratio > 50 ? 'text-red-600' : 'text-green-600' },
    repayment_capacity            && { label: 'Capacité remb.',    value: repayment_capacity,                 color: repayment_capacity === 'Élevée' ? 'text-green-600' : 'text-orange-600' },
    credit_limit_est !== undefined && { label: 'Limite crédit est.', value: `$${Math.round(credit_limit_est).toLocaleString()}M`, color: 'text-blue-600' },
    audit_score     !== undefined && { label: 'Score audit',       value: `${audit_score}/100`,               color: audit_score >= 80 ? 'text-green-600' : audit_score >= 60 ? 'text-orange-600' : 'text-red-600' },
    n_findings      !== undefined && { label: 'Non-conformités',   value: n_findings,                         color: n_findings === 0 ? 'text-green-600' : 'text-red-600' },
    viability_score !== undefined && { label: 'Score viabilité',   value: `${Math.round(viability_score)}%`,  color: viability_score >= 70 ? 'text-green-600' : viability_score >= 40 ? 'text-orange-600' : 'text-red-600' },
    action                        && { label: 'Action recommandée', value: action,                            color: 'text-blue-600' },
  ].filter(Boolean)

  if (!metrics.length) return null

  return (
    <div className="grid grid-cols-2 gap-2">
      {metrics.map((m, i) => (
        <div key={i} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
          <p className="text-xs text-gray-400">{m.label}</p>
          <p className={`text-sm font-bold mt-0.5 ${m.color}`}>{m.value}</p>
        </div>
      ))}
    </div>
  )
}

export default function ResultCard({ result, id, module }) {
  if (!result) return null

  const {
    verdict, alerts = [], red_flags = [], warnings = [],
    recommendations = [], findings = [], conformities = [],
    risk_level, risk_score, anomaly_type, _severity,
  } = result

  const allAlerts = [...alerts, ...red_flags, ...warnings]

  // Déterminer la sévérité
  const sevKey = _severity
    || (risk_level?.label?.toLowerCase().includes('critique') ? 'critique'
      : risk_level?.label?.toLowerCase().includes('élevé')    ? 'suspecte'
      : risk_level?.label?.toLowerCase().includes('modéré')   ? 'moderee'
      : 'normale')

  const sev = SEVERITY_CONFIG[sevKey] || SEVERITY_CONFIG.normale
  const level = sevKey === 'critique' ? 'critical'
              : sevKey === 'moderee'  ? 'high'
              : sevKey === 'suspecte' ? 'moderate'
              : 'low'

  const Icon = MODULE_ICONS[module] || Shield

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">

      {/* Header avec badge sévérité */}
      <div className={`px-6 py-4 border-b ${sev.border} ${sev.bg}
                       flex items-center justify-between`}>
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${sev.badge}`}>
            <Icon size={15} />
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">
              {MODULE_LABELS[module] || module}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`w-2 h-2 rounded-full ${sev.dot}`} />
              <span className={`text-xs font-bold ${sev.text}`}>{sev.label}</span>
            </div>
          </div>
        </div>
        {id && (
          <button
            onClick={() => downloadPDF(id)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium
                       text-blue-600 border border-blue-200 rounded-lg
                       hover:bg-blue-50 transition"
          >
            <Download size={12} /> PDF
          </button>
        )}
      </div>

      <div className="p-6 space-y-5">

        {/* Verdict */}
        {verdict && (
          <div className={`p-4 rounded-lg border ${sev.border} ${sev.bg}`}>
            <p className={`text-sm font-semibold ${sev.text}`}>{verdict}</p>
          </div>
        )}

        {/* Score VAE animé */}
        {risk_score !== undefined && (
          <AnimatedScore score={risk_score} />
        )}

        {/* Jauge de risque */}
        <RiskGauge level={level} score={risk_score} />

        {/* Type d'anomalie */}
        {anomaly_type && anomaly_type !== 'Normal' && anomaly_type !== '—' && (
          <div className="flex items-center gap-2 p-3 bg-red-50
                          border border-red-100 rounded-lg">
            <AlertTriangle size={14} className="text-red-500 flex-shrink-0" />
            <div>
              <p className="text-xs text-red-500 font-medium uppercase tracking-wide">
                Type détecté
              </p>
              <p className="text-xs text-red-700 font-semibold mt-0.5">{anomaly_type}</p>
            </div>
          </div>
        )}

        {/* Métriques spécifiques */}
        <MetricGrid result={result} />

        {/* Alertes */}
        {allAlerts.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              ⚠ Alertes détectées
            </p>
            <ul className="space-y-1.5">
              {allAlerts.map((a, i) => (
                <li key={i}
                    className="flex items-start gap-2 text-xs text-red-700
                               bg-red-50 p-2 rounded-lg border border-red-100">
                  <AlertTriangle size={11} className="mt-0.5 flex-shrink-0 text-red-500" />
                  {a}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Non-conformités audit */}
        {findings?.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Non-conformités
            </p>
            <ul className="space-y-2">
              {findings.map((f, i) => (
                <li key={i}
                    className="flex items-start gap-2 text-xs p-2
                               bg-red-50 rounded-lg border border-red-100">
                  <span className="px-1.5 py-0.5 rounded font-mono
                                   bg-red-200 text-red-800 text-xs shrink-0">
                    {f.code}
                  </span>
                  <span className="text-gray-700">{f.description}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Conformités */}
        {conformities?.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              ✓ Points conformes
            </p>
            <ul className="space-y-1.5">
              {conformities.map((c, i) => (
                <li key={i}
                    className="flex items-start gap-2 text-xs text-green-700
                               bg-green-50 p-2 rounded-lg border border-green-100">
                  <CheckCircle size={11} className="mt-0.5 flex-shrink-0 text-green-500" />
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommandations */}
        {recommendations.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              → Recommandations
            </p>
            <ul className="space-y-1.5">
              {recommendations.map((r, i) => (
                <li key={i}
                    className="flex items-start gap-2 text-xs text-gray-700
                               bg-blue-50 p-2 rounded-lg border border-blue-100">
                  <Info size={11} className="mt-0.5 flex-shrink-0 text-blue-400" />
                  {r}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Explication SHAP */}
        <Shapexplainer docId={id} score={risk_score} isAnomaly={result?._is_anomaly} />

        {/* Footer timestamp */}
        <p className="text-xs text-gray-300 text-right pt-2 border-t border-gray-50">
          {new Date().toLocaleDateString('fr-FR', {
            day: '2-digit', month: 'long', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
          })} · SynthGuard Intelligence v2.0
        </p>
      </div>
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-sm font-semibold text-gray-800 mt-0.5">{value}</p>
    </div>
  )
}