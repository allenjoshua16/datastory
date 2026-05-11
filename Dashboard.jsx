import StoryCard from '../components/StoryCard'
import ChartPanel from '../components/ChartPanel'
import MetaSummary from '../components/MetaSummary'

export default function Dashboard({ results, filename, onReset }) {
  const { metadata, stories, chart_specs, job_id } = results

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="flex items-start justify-between mb-8 gap-4">
        <div>
          <p className="text-xs font-mono text-muted mb-1 truncate">{filename}</p>
          <h1 className="font-serif text-3xl text-gold-light">Your Data Story</h1>
        </div>
        <div className="flex gap-3 flex-shrink-0">
          <a
            href={`/api/jobs/${job_id}/report`}
            target="_blank"
            rel="noreferrer"
            className="px-4 py-2 text-sm font-mono border border-gold-dark text-gold rounded-lg hover:bg-gold hover:text-ink transition-colors"
          >
            Full report ↗
          </a>
          <button
            onClick={onReset}
            className="px-4 py-2 text-sm font-mono border border-ink-600 text-muted rounded-lg hover:border-gold-dark hover:text-gold transition-colors"
          >
            New upload
          </button>
        </div>
      </div>

      {/* Metadata */}
      {metadata && <MetaSummary meta={metadata} />}

      {/* Stories */}
      {stories?.length > 0 && (
        <section className="mt-10">
          <h2 className="font-serif text-xl text-gold mb-4">Narratives</h2>
          <div className="space-y-3">
            {stories.map((s, i) => (
              <StoryCard key={i} story={s} index={i} />
            ))}
          </div>
        </section>
      )}

      {/* Charts */}
      {chart_specs?.length > 0 && (
        <section className="mt-10">
          <h2 className="font-serif text-xl text-gold mb-4">Visualizations</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {chart_specs.map((c) => (
              <ChartPanel key={c.chart_id} chart={c} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
