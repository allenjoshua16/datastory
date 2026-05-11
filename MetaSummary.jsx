export default function MetaSummary({ meta }) {
  const numericCols = meta.columns.filter(c => c.mean !== null && c.mean !== undefined)
  return (
    <div className="bg-ink-800 border border-ink-600 rounded-xl p-5">
      <p className="text-xs font-mono text-muted uppercase tracking-wider mb-4">Dataset summary</p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Stat label="Rows" value={meta.row_count.toLocaleString()} />
        <Stat label="Columns" value={meta.column_count} />
        <Stat label="Domain" value={meta.inferred_domain} />
        <Stat label="Anomalies" value={meta.anomalies.length} />
      </div>
      {meta.anomalies.length > 0 && (
        <div className="mt-4 space-y-1">
          {meta.anomalies.map((a, i) => (
            <p key={i} className="text-xs font-mono text-amber-500">⚠ {a}</p>
          ))}
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div>
      <p className="text-lg font-mono text-gold-light">{value}</p>
      <p className="text-xs text-muted uppercase tracking-wider">{label}</p>
    </div>
  )
}
