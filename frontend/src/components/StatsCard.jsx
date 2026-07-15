export default function StatsCard({ title, value, subtitle, color = 'blue', icon: Icon }) {
  const colors = {
    blue  : 'bg-blue-50   text-blue-600   border-blue-100',
    green : 'bg-green-50  text-green-600  border-green-100',
    red   : 'bg-red-50    text-red-600    border-red-100',
    amber : 'bg-amber-50  text-amber-600  border-amber-100',
    indigo: 'bg-indigo-50 text-indigo-600 border-indigo-100',
  }
  const cls = colors[color] || colors.blue

  return (
    <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wider font-medium">{title}</p>
          <p className="text-2xl font-bold text-gray-800 mt-1">{value ?? '—'}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={`p-2.5 rounded-lg border ${cls}`}>
            <Icon size={18} />
          </div>
        )}
      </div>
    </div>
  )
}