import { useState, useCallback } from 'react'
import { uploadDataset } from '../lib/api'

const AUDIENCE_OPTIONS = [
  { value: 'executive', label: 'Executive' },
  { value: 'analyst',   label: 'Analyst' },
  { value: 'investor',  label: 'Investor' },
  { value: 'general',   label: 'General' },
]
const ACCEPTED = ['.csv', '.xlsx', '.xls', '.xlsm']
const MAX_MB = 200

export default function UploadZone({ onJobCreated }) {
  const [dragging, setDragging]     = useState(false)
  const [audience, setAudience]     = useState('executive')
  const [uploading, setUploading]   = useState(false)
  const [fileError, setFileError]   = useState(null)
  const [pending, setPending]       = useState(null)   // file awaiting preprocess choice
  const [showModal, setShowModal]   = useState(false)

  const validateFile = (file) => {
    if (!file) return 'No file selected.'
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (!ACCEPTED.includes(ext)) return `Unsupported format. Accepted: ${ACCEPTED.join(', ')}`
    if (file.size > MAX_MB * 1024 * 1024)
      return `File too large (${(file.size/1024/1024).toFixed(1)} MB). Max ${MAX_MB} MB.`
    return null
  }

  const handleFile = useCallback((file) => {
    setFileError(null)
    const err = validateFile(file)
    if (err) { setFileError(err); return }
    setPending(file)
    setShowModal(true)
  }, [])

  const submit = async (preprocess) => {
    setShowModal(false)
    setUploading(true)
    try {
      const result = await uploadDataset(pending, audience, preprocess)
      onJobCreated(result.job_id, result.filename, preprocess)
    } catch (e) {
      setFileError(e.response?.data?.detail || e.message)
    } finally {
      setUploading(false)
      setPending(null)
    }
  }

  const onDrop = useCallback((e) => {
    e.preventDefault(); setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }, [handleFile])

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6">
      {/* Wordmark */}
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-serif font-normal tracking-tight text-gold-light">DataStory</h1>
        <p className="mt-2 text-sm text-muted font-mono tracking-widest uppercase">AI-augmented data storytelling</p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`w-full max-w-xl border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 cursor-pointer
          ${dragging ? 'drop-active bg-ink-700' : 'border-ink-600 hover:border-gold-dark hover:bg-ink-800'}`}
        onClick={() => !uploading && document.getElementById('file-input').click()}
      >
        {uploading ? (
          <>
            <div className="mb-4 text-3xl animate-pulse">⏳</div>
            <p className="text-gold font-serif text-lg">Uploading {pending?.name}…</p>
          </>
        ) : (
          <>
            <div className="mb-4 text-3xl">📂</div>
            <p className="text-gold font-serif text-lg">Drop your dataset here</p>
            <p className="text-muted text-sm mt-3 font-mono">CSV · Excel (.xlsx, .xls)</p>
            <p className="text-muted text-xs mt-1 font-mono">up to {MAX_MB} MB</p>
          </>
        )}
        <input id="file-input" type="file" className="hidden"
          accept={ACCEPTED.join(',')}
          onChange={(e) => handleFile(e.target.files[0])} />
      </div>

      {/* Audience selector */}
      <div className="mt-6 flex items-center gap-3 flex-wrap justify-center">
        <span className="text-muted text-sm font-mono">Narrative mode:</span>
        <div className="flex gap-2 flex-wrap">
          {AUDIENCE_OPTIONS.map(opt => (
            <button key={opt.value} onClick={() => setAudience(opt.value)}
              className={`px-3 py-1 rounded text-sm font-mono transition-colors
                ${audience === opt.value
                  ? 'bg-gold text-ink font-bold'
                  : 'bg-ink-800 text-muted border border-ink-600 hover:border-gold-dark hover:text-gold'}`}>
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {fileError && <p className="mt-4 text-sm text-red-400 font-mono max-w-md text-center">{fileError}</p>}

      {/* Formats grid */}
      <div className="mt-10 grid grid-cols-3 gap-3 max-w-lg text-center">
        {[
          {icon:'📊', label:'CSV',          desc:'Comma-separated values'},
          {icon:'📗', label:'Excel',        desc:'.xlsx, .xls, .xlsm'},
          {icon:'🔒', label:'Private',      desc:'Session only, not stored'},
        ].map(f => (
          <div key={f.label} className="bg-ink-800 border border-ink-600 rounded-lg p-3">
            <div className="text-lg mb-1">{f.icon}</div>
            <div className="text-xs font-mono text-gold">{f.label}</div>
            <div className="text-xs text-muted mt-0.5">{f.desc}</div>
          </div>
        ))}
      </div>

      {/* Preprocess Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4">
          <div className="bg-ink-800 border border-ink-600 rounded-2xl p-8 max-w-md w-full shadow-2xl">
            <h2 className="font-serif text-xl text-gold-light mb-2">How should we handle your data?</h2>
            <p className="text-muted text-sm font-mono mb-1 truncate">📂 {pending?.name}</p>
            <p className="text-muted text-sm mb-6">
              Choose whether to clean and standardize your data before analysis, or dive straight in.
            </p>

            <div className="space-y-3">
              <button onClick={() => submit(true)}
                className="w-full bg-gold/10 border border-gold rounded-xl p-4 text-left hover:bg-gold/20 transition-colors group">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">🧹</span>
                  <div>
                    <div className="font-mono text-gold font-bold group-hover:text-gold-light">Preprocess & Analyze</div>
                    <div className="text-xs text-muted mt-0.5">
                      Fix missing values, remove duplicates, detect outliers, clean column names, extract date features
                    </div>
                  </div>
                </div>
              </button>

              <button onClick={() => submit(false)}
                className="w-full bg-ink-700 border border-ink-600 rounded-xl p-4 text-left hover:border-gold-dark transition-colors group">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">⚡</span>
                  <div>
                    <div className="font-mono text-gray-300 font-bold group-hover:text-gold">Analyze Immediately</div>
                    <div className="text-xs text-muted mt-0.5">
                      Skip preprocessing — analyze the dataset as-is
                    </div>
                  </div>
                </div>
              </button>
            </div>

            <button onClick={() => { setShowModal(false); setPending(null) }}
              className="mt-4 w-full text-center text-xs text-muted hover:text-gold font-mono py-2">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
