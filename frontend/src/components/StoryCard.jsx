import { useState } from 'react'
import clsx from 'clsx'

export default function StoryCard({ story, index }) {
  const [expanded, setExpanded] = useState(index === 0)

  return (
    <div className="border border-ink-600 rounded-xl overflow-hidden transition-colors hover:border-gold-dark">
      <button
        className="w-full text-left px-6 py-4 flex items-start justify-between gap-4"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-muted">
              score {story.score?.toFixed(2)} · {story.audience_mode}
            </span>
          </div>
          <h3 className="font-serif text-lg text-gold-light leading-tight">{story.title}</h3>
          <p className="text-muted text-sm mt-1 italic">{story.hook}</p>
        </div>
        <span className={clsx('text-gold mt-1 transition-transform', expanded && 'rotate-90')}>›</span>
      </button>

      {expanded && (
        <div className="px-6 pb-6 border-t border-ink-600 pt-4">
          <div className="grid grid-cols-3 gap-4 mb-5 text-sm">
            <div>
              <p className="text-xs font-mono text-muted uppercase tracking-wider mb-1">Context</p>
              <p className="text-gray-300">{story.context}</p>
            </div>
            <div>
              <p className="text-xs font-mono text-muted uppercase tracking-wider mb-1">Finding</p>
              <p className="text-gray-300">{story.dispute}</p>
            </div>
            <div>
              <p className="text-xs font-mono text-muted uppercase tracking-wider mb-1">Action</p>
              <p className="text-gray-300">{story.solution}</p>
            </div>
          </div>
          <div className="border-l-2 border-gold-dark pl-4">
            <p className="text-sm leading-relaxed text-gray-200">{story.narrative_text}</p>
          </div>
        </div>
      )}
    </div>
  )
}
