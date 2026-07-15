const RISK_CONFIG = {
  low     : { label: 'Faible',   color: '#10b981', bg: 'bg-green-50',  text: 'text-green-700',  border: 'border-green-200', pct: 15  },
  moderate: { label: 'Modéré',   color: '#f59e0b', bg: 'bg-amber-50',  text: 'text-amber-700',  border: 'border-amber-200', pct: 40  },
  high    : { label: 'Élevé',    color: '#f97316', bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200',pct: 70  },
  critical: { label: 'Critique', color: '#ef4444', bg: 'bg-red-50',    text: 'text-red-700',    border: 'border-red-200',   pct: 95  },
  normale : { label: 'Normal',   color: '#10b981', bg: 'bg-green-50',  text: 'text-green-700',  border: 'border-green-200', pct: 10  },
  suspecte: { label: 'Suspect',  color: '#f59e0b', bg: 'bg-amber-50',  text: 'text-amber-700',  border: 'border-amber-200', pct: 35  },
  moderee : { label: 'Modéré',   color: '#f97316', bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200',pct: 65  },
  critique: { label: 'Critique', color: '#ef4444', bg: 'bg-red-50',    text: 'text-red-700',    border: 'border-red-200',   pct: 95  },
}

export default function RiskGauge({ level = 'low', score }) {
  const cfg = RISK_CONFIG[level] || RISK_CONFIG.low
  const pct = cfg.pct

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-600">Niveau de risque</span>
        <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
          {cfg.label}
        </span>
      </div>

      {/* Barre de progression */}
      <div className="relative h-3 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: cfg.color }}
        />
      </div>

      {/* Étiquettes */}
      <div className="flex justify-between text-xs text-gray-400">
        <span>Faible</span>
        <span>Modéré</span>
        <span>Élevé</span>
        <span>Critique</span>
      </div>

      {/* Score VAE */}
      {score !== undefined && (
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs text-gray-400">Score VAE</span>
          <span className="font-mono text-xs font-medium" style={{ color: cfg.color }}>
            {typeof score === 'number' ? score.toFixed(6) : score}
          </span>
        </div>
      )}
    </div>
  )
}