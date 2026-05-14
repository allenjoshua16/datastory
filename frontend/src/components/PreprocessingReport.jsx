import { useState } from 'react'

export default function PreprocessingReport({ report, jobId }) {
  const [open, setOpen] = useState(false)
  if (!report) return null

  const pctRemoved = report.row_count_before > 0
    ? ((report.rows_removed / report.row_count_before) * 100).toFixed(1)
    : 0

  return (
    <div className="bg-ink-800 border border-ink-600 rounded-xl overflow-hidden mb-6">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-ink-700 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">🧹</span>
          <div className="text-left">
            <p className="font-mono text-sm text-gold">Preprocessing Summary</p>
            <p className="text-xs text-muted mt-0.5">
              {report.transformations.length} transformations · {report.rows_removed} rows removed · {report.columns_removed} columns removed
            </p>
          </div>
        </div>
        <span className={`text-gold transition-transform ${open ? 'rotate-90' : ''}`}>›</span>
      </button>

      {open && (
        <div className="px-6 pb-6 border-t border-ink-600 pt-4">
          {/* Stats grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
            <Stat label="Rows before" value={report.row_count_before.toLocaleString()} />
            <Stat label="Rows after"  value={report.row_count_after.toLocaleString()}  color="text-green-400" />
            <Stat label="Removed"     value={`${report.rows_removed} (${pctRemoved}%)`} color="text-amber-400" />
            <Stat label="Columns"     value={`${report.column_count_before} → ${report.column_count_after}`} />
          </div>

          {/* Transformations */}
          {report.transformations.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-mono text-muted uppercase tracking-wider mb-2">Transformations applied</p>
              <ul className="space-y-1">
                {report.transformations.map((t, i) => (
                  <li key={i} className="flex gap-2 text-xs font-mono text-gray-400 bg-ink-700 rounded px-3 py-1.5">
                    <span className="text-green-400 flex-shrink-0">✓</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Inferred types */}
          {report.inferred_types && Object.keys(report.inferred_types).length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-mono text-muted uppercase tracking-wider mb-2">Inferred column types</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(report.inferred_types).map(([col, dtype]) => (
                  <span key={col}
                    className={`px-2 py-0.5 rounded text-xs font-mono border
                      ${dtype === 'datetime' ? 'bg-blue-950 text-blue-300 border-blue-800'
                      : dtype === 'numeric'  ? 'bg-green-950 text-green-300 border-green-800'
                      : 'bg-ink-700 text-muted border-ink-600'}`}>
                    {col}: {dtype}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Download cleaned */}
          <a
            href={`${import.meta.env.VITE_API_URL || ''}/api/jobs/${jobId}/cleaned`}
            download
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-mono border border-gold-dark text-gold rounded-lg hover:bg-gold hover:text-ink transition-colors"
          >
            ⬇ Download cleaned dataset
          </a>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, color = 'text-gold-light' }) {
  return (
    <div className="bg-ink-700 rounded-lg p-3">
      <p className={`text-sm font-mono ${color}`}>{value}</p>
      <p className="text-xs text-muted uppercase tracking-wider mt-0.5">{label}</p>
    </div>
  )
}
