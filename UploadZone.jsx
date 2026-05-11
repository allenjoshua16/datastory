import { useState, useCallback } from 'react'
import { uploadDataset } from '../lib/api'

const AUDIENCE_OPTIONS = [
  { value: 'executive', label: 'Executive' },
  { value: 'analyst', label: 'Analyst' },
  { value: 'investor', label: 'Investor' },
  { value: 'general', label: 'General' },
]

export default function UploadZone({ onJobCreated }) {
  const [dragging, setDragging] = useState(false)
  const [audience, setAudience] = useState('executive')
  const [uploading, setUploading] = useState(false)
  const [fileError, setFileError] = useState(null)

  const handleFile = useCallback(async (file) => {
    setFileError(null)
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['csv', 'xlsx', 'xls', 'json'].includes(ext)) {
      setFileError('Upload a CSV, Excel, or JSON file.')
      return
    }
    setUploading(true)
    try {
      const result = await uploadDataset(file, audience)
      onJobCreated(result.job_id, result.filename)
    } catch (e) {
      setFileError(e.response?.data?.detail || e.message)
    } finally {
      setUploading(false)
    }
  }, [audience, onJobCreated])

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }, [handleFile])

  const onInputChange = (e) => handleFile(e.target.files[0])

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6">
      {/* Wordmark */}
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-serif font-normal tracking-tight text-gold-light">
          DataStory
        </h1>
        <p className="mt-2 text-sm text-muted font-mono tracking-widest uppercase">
          AI-augmented data storytelling
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`w-full max-w-xl border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 cursor-pointer
          ${dragging ? 'drop-active bg-ink-700' : 'border-ink-600 hover:border-gold-dark hover:bg-ink-800'}`}
        onClick={() => document.getElementById('file-input').click()}
      >
        <div className="mb-4 text-3xl">📊</div>
        <p className="text-gold font-serif text-lg">Drop your dataset here</p>
        <p className="text-muted text-sm mt-2 font-mono">CSV · Excel · JSON &nbsp;·&nbsp; max 50 MB</p>
        <input
          id="file-input" type="file" className="hidden"
          accept=".csv,.xlsx,.xls,.json"
          onChange={onInputChange}
        />
      </div>

      {/* Audience selector */}
      <div className="mt-6 flex items-center gap-3">
        <span className="text-muted text-sm font-mono">Narrative mode:</span>
        <div className="flex gap-2">
          {AUDIENCE_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setAudience(opt.value)}
              className={`px-3 py-1 rounded text-sm font-mono transition-colors
                ${audience === opt.value
                  ? 'bg-gold text-ink font-bold'
                  : 'bg-ink-800 text-muted border border-ink-600 hover:border-gold-dark hover:text-gold'}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {fileError && (
        <p className="mt-4 text-sm text-red-400 font-mono">{fileError}</p>
      )}
      {uploading && (
        <p className="mt-4 text-sm text-gold font-mono animate-pulse">Uploading…</p>
      )}

      <p className="mt-12 text-xs text-muted font-mono max-w-sm text-center">
        Your data is processed in memory and never stored permanently.
        Reports are retained for your session only.
      </p>
    </div>
  )
}
