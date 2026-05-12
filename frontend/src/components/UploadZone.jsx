import { useState, useCallback } from 'react'
import { uploadDataset } from '../lib/api'

const AUDIENCE_OPTIONS = [
  { value: 'executive', label: 'Executive' },
  { value: 'analyst',   label: 'Analyst' },
  { value: 'investor',  label: 'Investor' },
  { value: 'general',   label: 'General' },
]

const ACCEPTED_EXTENSIONS = ['.csv', '.xlsx', '.xls', '.xlsm', '.json', '.tsv', '.parquet', '.docx']
const MAX_SIZE_MB = 200

export default function UploadZone({ onJobCreated }) {
  const [dragging, setDragging]   = useState(false)
  const [audience, setAudience]   = useState('executive')
  const [uploading, setUploading] = useState(false)
  const [fileError, setFileError] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)

  const handleFile = useCallback(async (file) => {
    setFileError(null)
    if (!file) return

    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      setFileError(`Unsupported format. Accepted: ${ACCEPTED_EXTENSIONS.join(', ')}`)
      return
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setFileError(`File too large (${(file.size/1024/1024).toFixed(1)} MB). Max is ${MAX_SIZE_MB} MB.`)
      return
    }

    setSelectedFile(file)
    setUploading(true)
    try {
      const result = await uploadDataset(file, audience)
      onJobCreated(result.job_id, result.filename)
    } catch (e) {
      setFileError(e.response?.data?.detail || e.message)
      setSelectedFile(null)
    } finally {
      setUploading(false)
    }
  }, [audience, onJobCreated])

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
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
        onClick={() => document.getElementById('file-input').click()}
      >
        {uploading ? (
          <>
            <div className="mb-4 text-3xl animate-pulse">⏳</div>
            <p className="text-gold font-serif text-lg">Uploading {selectedFile?.name}…</p>
            <p className="text-muted text-sm mt-2 font-mono">{(selectedFile?.size / 1024 / 1024).toFixed(1)} MB</p>
          </>
        ) : (
          <>
            <div className="mb-4 text-3xl">📂</div>
            <p className="text-gold font-serif text-lg">Drop your dataset here</p>
            <p className="text-muted text-sm mt-3 font-mono leading-relaxed">
              CSV · Excel · JSON · TSV · Parquet · DOCX
            </p>
            <p className="text-muted text-xs mt-2 font-mono">up to {MAX_SIZE_MB} MB</p>
          </>
        )}
        <input
          id="file-input" type="file" className="hidden"
          accept={ACCEPTED_EXTENSIONS.join(',')}
          onChange={(e) => handleFile(e.target.files[0])}
        />
      </div>

      {/* Audience selector */}
      <div className="mt-6 flex items-center gap-3 flex-wrap justify-center">
        <span className="text-muted text-sm font-mono">Narrative mode:</span>
        <div className="flex gap-2 flex-wrap">
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
        <p className="mt-4 text-sm text-red-400 font-mono max-w-md text-center">{fileError}</p>
      )}

      {/* Supported formats legend */}
      <div className="mt-10 grid grid-cols-3 gap-3 max-w-lg text-center">
        {[
          { icon: '📊', label: 'CSV / TSV', desc: 'Comma or tab separated' },
          { icon: '📗', label: 'Excel', desc: '.xlsx, .xls, .xlsm' },
          { icon: '📄', label: 'JSON', desc: 'Array or object format' },
          { icon: '📦', label: 'Parquet', desc: 'Columnar data files' },
          { icon: '📝', label: 'Word', desc: '.docx with tables' },
          { icon: '🔒', label: 'Private', desc: 'Session only, not stored' },
        ].map(f => (
          <div key={f.label} className="bg-ink-800 border border-ink-600 rounded-lg p-3">
            <div className="text-lg mb-1">{f.icon}</div>
            <div className="text-xs font-mono text-gold">{f.label}</div>
            <div className="text-xs text-muted mt-0.5">{f.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
