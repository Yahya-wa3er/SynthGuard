import { useState, useEffect, useRef } from 'react'
import { analyzeCreditRisk , getHistory } from '../services/api'
import AnalysisForm from '../components/AnalysisForm'
import ResultCard from '../components/ResultCard'

export default function CreditRisk() {
  const [result,   setResult  ] = useState(null)
  const [loading,  setLoading ] = useState(false)
  const [error,    setError   ] = useState(null)
  const [docId,    setDocId   ] = useState(null)
  const [waiting,  setWaiting ] = useState(false)
  const lastAccount = useRef(null)
  const pollTimer   = useRef(null)

  useEffect(() => () => clearInterval(pollTimer.current), [])

  const pollForResult = (accountName) => {
    let attempts = 0
    const MAX = 30
    setWaiting(true)
    pollTimer.current = setInterval(async () => {
      attempts++
      try {
        const res = await getHistory({ page: 0, per_page: 5 })
        const docs = res.data?.docs || []
        const found = docs.find(
          d => d.account === accountName && d.module === 'credit_risk'
        )
        if (found) {
          clearInterval(pollTimer.current)
          setWaiting(false)
          setDocId(found.id)
          setResult({
            verdict        : found.interpretation?.verdict || '—',
            alerts         : found.interpretation?.alerts || [],
            recommendations: found.interpretation?.recommendations || [],
            risk_level     : { label: found.severity === 'critique' ? 'Critique'
                                     : found.severity === 'moderee'  ? 'Modéré'
                                     : found.severity === 'suspecte' ? 'Élevé'
                                     : 'Faible' },
            risk_score     : found.score,
            anomaly_type   : found.anomaly_label,
            _severity      : found.severity,
            _is_anomaly    : found.is_anomaly,
          })
        } else if (attempts >= MAX) {
          clearInterval(pollTimer.current)
          setWaiting(false)
          setError("Délai dépassé — vérifiez l'historique dans quelques instants")
        }
      } catch {}
    }, 500)
  }

  const handleSubmit = async (data) => {
    setLoading(true); setError(null); setResult(null)
    lastAccount.current = data.account
    clearInterval(pollTimer.current)
    try {
      const res = await analyzeCreditRisk(data)
      if (res.data.status === 'ok') {
        setResult(res.data.result)
        setDocId(res.data.id)
      } else {
        pollForResult(data.account)
      }
    } catch (e) {
      setError(e.response?.data?.error || 'Erreur de connexion au serveur')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-primary">Credit Risk</h1>
        <p className="text-sm text-gray-400 mt-1">Évaluez la solvabilité avant accord de crédit</p>
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="card p-6">
          <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-5">
            Saisie des données
          </h2>
          <AnalysisForm onSubmit={handleSubmit} loading={loading || waiting} />
          {waiting && !error && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded-lg
                            flex items-center gap-3 text-xs text-blue-700">
              <svg className="animate-spin h-4 w-4 text-blue-500 flex-shrink-0"
                   fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10"
                        stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              Analyse en cours — récupération du résultat...
            </div>
          )}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-lg
                            text-xs text-red-600">
              {error}
            </div>
          )}
        </div>
        <div>
          {result ? (
            <ResultCard result={result} id={docId} module="credit_risk" />
          ) : (
            <div className="card p-6 flex flex-col items-center justify-center
                            h-full min-h-[300px] text-center">
              {waiting ? (
                <>
                  <div className="w-14 h-14 bg-blue-50 rounded-full flex items-center
                                  justify-center mb-4 animate-pulse">
                    <svg className="animate-spin h-6 w-6 text-blue-400"
                         fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10"
                              stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor"
                            d="M4 12a8 8 0 018-8v8H4z"/>
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-blue-500">
                    Moteur IA en cours d'analyse...
                  </p>
                  <p className="text-xs text-gray-300 mt-1">
                    Score VAE · Détection · Interprétation métier
                  </p>
                </>
              ) : (
                <>
                  <div className="w-14 h-14 bg-blue-50 rounded-full flex items-center
                                  justify-center mb-4">
                    <span className="text-2xl">⬡</span>
                  </div>
                  <p className="text-sm font-medium text-gray-500">En attente d'analyse</p>
                  <p className="text-xs text-gray-300 mt-1">
                    Remplissez le formulaire et lancez l'analyse IA
                  </p>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}