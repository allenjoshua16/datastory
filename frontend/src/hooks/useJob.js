import { useState, useEffect, useRef, useCallback } from 'react'
import { connectJobWebSocket, getJobResults } from '../lib/api'

export function useJob(jobId) {
  const [status, setStatus] = useState('queued')
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const wsRef = useRef(null)

  const fetchResults = useCallback(async () => {
    try {
      const data = await getJobResults(jobId)
      setResults(data)
    } catch (e) {
      setError(e.message)
    }
  }, [jobId])

  useEffect(() => {
    if (!jobId) return
    const ws = connectJobWebSocket(jobId, (update) => {
      if (update.ping) return
      if (update.error) { setError(update.error); return }
      setStatus(update.status)
      setProgress(update.progress ?? 0)
      setMessage(update.message ?? '')
      if (update.status === 'done') fetchResults()
      if (update.status === 'error') setError(update.error || 'Pipeline failed')
    })
    wsRef.current = ws
    return () => ws.close()
  }, [jobId, fetchResults])

  return { status, progress, message, results, error }
}
