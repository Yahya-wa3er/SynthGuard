import { useState, useRef, useEffect } from 'react'
import { getStats, getHistory } from '../services/api'
import { MessageCircle, X, Send, Loader, Bot, User, Minimize2, Maximize2 } from 'lucide-react'

// ── Chargement du contexte Markdown ─────────────────────────────────────────
import SYNTHGUARD_MD from '../../SYNTHGUARD_CONTEXT.md?raw'

// ── Prompt système ────────────────────────────────────────────────────────────
const buildSystemPrompt = (stats, recentDocs) => {
  const topAnomalies = (recentDocs || [])
    .filter(d => d.is_anomaly)
    .sort((a, b) => (b.score || 0) - (a.score || 0))
    .slice(0, 8)
    .map(d => `- ${d.account} (${d.sector}) : score=${d.score?.toFixed(5)}, sévérité=${d.severity}, type=${d.anomaly_label || '—'}, module=${d.module}`)
    .join('\n')

  const moduleBreakdown = Object.entries(stats?.by_module || {})
    .map(([mod, data]) => {
      const rate = data.count > 0 ? ((data.anomalies/data.count)*100).toFixed(1) : 0
      return `  - ${mod}: ${data.count} analyses, ${data.anomalies} anomalies (${rate}%)`
    })
    .join('\n')

  const severityBreakdown = Object.entries(stats?.by_severity || {})
    .map(([sev, count]) => `  - ${sev}: ${count}`)
    .join('\n')

  return `${SYNTHGUARD_MD}

=== DONNÉES EN TEMPS RÉEL (snapshot actuel de la plateforme) ===
Date snapshot : ${new Date().toLocaleString('fr-FR')}
Total analyses : ${stats?.total?.toLocaleString() || '—'}
Anomalies détectées : ${stats?.anomalies?.toLocaleString() || '—'} (${stats?.rate || 0}% du total)
Score VAE moyen : ${stats?.avg_score?.toFixed(5) || '—'}
Taux de conformité : ${stats ? (100 - (stats.rate || 0)).toFixed(1) : '—'}%

Répartition par sévérité :
${severityBreakdown || '  Aucune donnée'}

Répartition par module :
${moduleBreakdown || '  Aucune donnée'}

Top anomalies récentes (score VAE décroissant) :
${topAnomalies || '  Aucune anomalie récente'}
`
}

// ── Suggestions rapides ────────────────────────────────────────────────────────
const QUICK_SUGGESTIONS = [
  "Explique le score VAE",
  "Combien d'anomalies détectées ?",
  "Quels sont les 5 modules ?",
  "Comment fonctionne le Beta-VAE ?",
  "Quel est le seuil de détection ?",
  "Quels types d'anomalies existent ?",
]

// ── Bulle de message ──────────────────────────────────────────────────────────
function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5
        ${isUser ? 'bg-blue-600' : 'bg-gradient-to-br from-blue-800 to-blue-600'}`}>
        {isUser
          ? <User size={13} className="text-white" />
          : <Bot  size={13} className="text-white" />}
      </div>
      <div className={`max-w-[82%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed
        ${isUser
          ? 'bg-blue-600 text-white rounded-tr-sm'
          : 'bg-gray-100 text-gray-800 rounded-tl-sm'}`}>
        {msg.content.split('\n').map((line, i) => (
          <span key={i}>{line}{i < msg.content.split('\n').length - 1 && <br />}</span>
        ))}
        <p className={`text-xs mt-1 ${isUser ? 'text-blue-200' : 'text-gray-400'}`}>
          {msg.time}
        </p>
      </div>
    </div>
  )
}

// ── Composant principal ───────────────────────────────────────────────────────
export default function SynthGuardChat() {
  const [open,      setOpen     ] = useState(false)
  const [expanded,  setExpanded ] = useState(false)
  const [messages,  setMessages ] = useState([])
  const [input,     setInput    ] = useState('')
  const [loading,   setLoading  ] = useState(false)
  const [stats,     setStats    ] = useState(null)
  const [docs,      setDocs     ] = useState([])
  const [hasNew,    setHasNew   ] = useState(false)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)

  // Charger le contexte dashboard au montage
  useEffect(() => {
    const loadCtx = async () => {
      try {
        const [sRes, hRes] = await Promise.all([
          getStats(),
          getHistory({ page: 0, per_page: 50 }),
        ])
        setStats(sRes.data)
        setDocs(hRes.data?.docs || [])
      } catch {}
    }
    loadCtx()
  }, [])

  // Message de bienvenue à l'ouverture
  useEffect(() => {
    if (open && messages.length === 0) {
      const now = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
      setMessages([{
        role   : 'assistant',
        content: `Bonjour ! Je suis **SynthGuard Assistant**, votre expert IA intégré.\n\nJ'ai accès aux données en temps réel de la plateforme — ${stats?.total?.toLocaleString() || '…'} analyses, ${stats?.anomalies?.toLocaleString() || '…'} anomalies détectées.\n\nComment puis-je vous aider ?`,
        time   : now,
      }])
      setTimeout(() => inputRef.current?.focus(), 100)
    }
    if (open) setHasNew(false)
  }, [open])

  // Scroll automatique
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const now = () => new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })

  const sendMessage = async (text) => {
    const userText = (text || input).trim()
    if (!userText || loading) return
    setInput('')

    const userMsg = { role: 'user', content: userText, time: now() }
    const history = [...messages, userMsg]
    setMessages(history)
    setLoading(true)

    try {
      // ── Appel API OpenRouter — Claude Sonnet 5 ──────────────────────
      const OR_KEY = import.meta.env.VITE_OPENROUTER_API_KEY
      const OR_URL = import.meta.env.VITE_OPENROUTER_BASE_URL || 'https://openrouter.ai/api/v1'

      const response = await fetch(`${OR_URL}/chat/completions`, {
        method : 'POST',
        headers: {
          'Content-Type' : 'application/json',
          'Authorization': `Bearer ${OR_KEY}`,
          'HTTP-Referer' : 'http://localhost:3000',
          'X-Title'      : 'SynthGuard Intelligence',
        },
        body: JSON.stringify({
          model      : 'anthropic/claude-sonnet-5',
          max_tokens : 1000,
          temperature: 0.7,
          messages   : [
            { role: 'system', content: buildSystemPrompt(stats, docs) },
            ...history
              .filter(m => m.role !== 'system')
              .map(m => ({ role: m.role, content: m.content })),
          ],
        }),
      })

      const data  = await response.json()
      const reply = data.choices?.[0]?.message?.content
                 || "Désolé, je n'ai pas pu générer de réponse."

      setMessages(prev => [...prev, {
        role   : 'assistant',
        content: reply,
        time   : now(),
      }])

      if (!open) setHasNew(true)
    } catch (e) {
      setMessages(prev => [...prev, {
        role   : 'assistant',
        content: "Erreur de connexion à l'API. Vérifiez votre connexion réseau.",
        time   : now(),
      }])
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
    setTimeout(() => setOpen(true), 10)
  }

  const toggleExpand = () => setExpanded(e => !e)

  // Dimensions selon le mode
  const panelClass = expanded
    ? 'fixed bottom-6 right-6 z-50 flex flex-col overflow-hidden rounded-2xl shadow-2xl border border-gray-100 bg-white'
    : 'fixed bottom-24 right-6 z-50 flex flex-col overflow-hidden rounded-2xl shadow-2xl border border-gray-100 bg-white'

  const panelStyle = expanded
    ? { width: '680px', height: '80vh', maxHeight: '800px' }
    : { width: '420px', height: '580px' }

  return (
    <>
      {/* ── Bouton flottant ─────────────────────────────────────────────── */}
      <button
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg
                   bg-gradient-to-br from-blue-700 to-blue-900
                   flex items-center justify-center
                   hover:scale-105 active:scale-95 transition-transform"
        aria-label="Ouvrir le chatbot SynthGuard"
      >
        {open
          ? <X size={22} className="text-white" />
          : <MessageCircle size={22} className="text-white" />}
        {hasNew && !open && (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full
                           flex items-center justify-center text-white text-xs font-bold">
            !
          </span>
        )}
      </button>

      {/* ── Panneau chat ────────────────────────────────────────────────── */}
      {open && (
        <div className={panelClass} style={panelStyle}>

          {/* Header */}
          <div className="bg-gradient-to-r from-blue-800 to-blue-700 px-4 py-3
                          flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <Bot size={16} className="text-white" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">SynthGuard Assistant</p>
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                  <p className="text-xs text-blue-200">
                    Claude Sonnet 5 · Données temps réel
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button onClick={clearChat}
                className="p-1.5 rounded-lg hover:bg-white/10 transition
                           text-blue-200 hover:text-white text-xs">
                Effacer
              </button>
              {/* Bouton Agrandir / Réduire */}
              <button
                onClick={toggleExpand}
                title={expanded ? 'Réduire' : 'Agrandir'}
                className="p-1.5 rounded-lg hover:bg-white/10 transition"
              >
                {expanded
                  ? <Minimize2 size={15} className="text-blue-200" />
                  : <Maximize2 size={15} className="text-blue-200" />}
              </button>
              {/* Bouton Fermer */}
              <button
                onClick={() => { setOpen(false); setExpanded(false) }}
                className="p-1.5 rounded-lg hover:bg-white/10 transition"
              >
                <X size={15} className="text-blue-200" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}

            {/* Indicateur typing */}
            {loading && (
              <div className="flex gap-2.5">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-800 to-blue-600
                                flex items-center justify-center flex-shrink-0">
                  <Bot size={13} className="text-white" />
                </div>
                <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3">
                  <div className="flex gap-1 items-center h-4">
                    {[0,1,2].map(i => (
                      <span key={i}
                        className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                        style={{ animationDelay: `${i * 150}ms` }} />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Suggestions rapides */}
          {messages.length <= 1 && !loading && (
            <div className="px-4 pb-2 flex-shrink-0">
              <p className="text-xs text-gray-400 mb-2">Suggestions :</p>
              <div className="flex flex-wrap gap-1.5">
                {QUICK_SUGGESTIONS.map((s, i) => (
                  <button key={i} onClick={() => sendMessage(s)}
                    className="px-2.5 py-1 rounded-full text-xs bg-blue-50 text-blue-700
                               border border-blue-100 hover:bg-blue-100 transition">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="px-4 py-3 border-t border-gray-100 flex-shrink-0">
            <div className="flex gap-2 items-end">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Posez une question sur les analyses..."
                rows={expanded ? 2 : 1}
                className="flex-1 resize-none rounded-xl border border-gray-200
                           px-3 py-2.5 text-sm text-gray-700 placeholder-gray-400
                           focus:outline-none focus:ring-2 focus:ring-blue-200
                           focus:border-blue-400 transition max-h-32 overflow-y-auto"
                style={{ lineHeight: '1.4' }}
              />
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim() || loading}
                className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center
                           hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed
                           transition flex-shrink-0"
              >
                {loading
                  ? <Loader size={15} className="text-white animate-spin" />
                  : <Send   size={15} className="text-white" />}
              </button>
            </div>
            <p className="text-xs text-gray-300 mt-1.5 text-center">
              Entrée pour envoyer · Shift+Entrée pour nouvelle ligne
            </p>
          </div>
        </div>
      )}
    </>
  )
}