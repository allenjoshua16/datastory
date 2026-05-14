const STAGES = [
  { key: 'preprocessing', label: 'Preprocessing data'   },
  { key: 'analyzing',     label: 'Analyzing structure'  },
  { key: 'visualizing',   label: 'Selecting charts'     },
  { key: 'executing',     label: 'Rendering visuals'    },
  { key: 'generating',    label: 'Writing narratives'   },
  { key: 'reporting',     label: 'Assembling report'    },
  { key: 'done',          label: 'Done'                 },
]
const ORDER = STAGES.map(s => s.key)

export default function PipelineProgress({ filename, status, progress, message, error, preprocess }) {
  const visibleStages = preprocess ? STAGES : STAGES.filter(s => s.key !== 'preprocessing')
  const current = ORDER.indexOf(status)

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-lg">
        <p className="text-muted text-xs font-mono mb-2 truncate">{filename}</p>
        <h2 className="font-serif text-2xl text-gold-light mb-8">
          {status === 'error' ? 'Something went wrong' : 'Building your story…'}
        </h2>

        <div className="space-y-4 mb-10">
          {visibleStages.map((stage, i) => {
            const stageIdx = ORDER.indexOf(stage.key)
            const done   = stageIdx < current
            const active = stageIdx === current
            return (
              <div key={stage.key} className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono flex-shrink-0 transition-colors duration-500
                  ${done ? 'bg-gold text-ink' : active ? 'border-2 border-gold text-gold animate-pulse' : 'border border-ink-600 text-muted'}`}>
                  {done ? '✓' : i + 1}
                </div>
                <span className={`text-sm font-mono transition-colors duration-300
                  ${done ? 'text-gold-dark' : active ? 'text-gold' : 'text-muted'}`}>
                  {stage.label}
                  {stage.key === 'preprocessing' && <span className="ml-1 text-xs text-muted">(cleaning data)</span>}
                </span>
                {active && message && (
                  <span className="text-xs text-muted ml-auto truncate max-w-[200px]">{message}</span>
                )}
              </div>
            )
          })}
        </div>

        <div className="h-1 bg-ink-700 rounded-full overflow-hidden">
          <div className="h-full progress-bar rounded-full transition-all duration-700"
               style={{ width: `${progress}%` }} />
        </div>
        <p className="text-right text-xs text-muted font-mono mt-1">{progress}%</p>

        {error && (
          <div className="mt-6 bg-red-950 border border-red-800 rounded-lg p-4 text-sm text-red-300 font-mono">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}
