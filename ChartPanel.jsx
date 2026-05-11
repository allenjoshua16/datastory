export default function ChartPanel({ chart }) {
  return (
    <div className="bg-ink-800 rounded-xl overflow-hidden border border-ink-600">
      <div className="px-4 py-3 border-b border-ink-600">
        <p className="text-sm font-mono text-gold">{chart.title}</p>
        <p className="text-xs text-muted mt-0.5">{chart.rationale}</p>
      </div>
      {chart.rendered_html ? (
        <iframe
          srcDoc={chart.rendered_html}
          className="w-full"
          style={{ height: 380, border: 'none', background: '#fff' }}
          title={chart.title}
          sandbox="allow-scripts"
        />
      ) : (
        <div className="h-48 flex items-center justify-center text-muted text-sm font-mono">
          Chart unavailable
        </div>
      )}
    </div>
  )
}
