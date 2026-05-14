import { useState, useEffect, useRef, useCallback } from 'react'
import { connectJobWebSocket, getJobResults, getJobStatus } from '../lib/api'

export function useJob(jobId) {
  const [status, setStatus]   = useState('queued')
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [results, setResults] = useState(null)
  const [error, setError]     = useState(null)
  const wsRef    = useRef(null)
  const pollRef  = useRef(null)
  const mountedRef = useRef(true)

  const fetchResults = useCallback(async () => {
    try {
      const data = await getJobResults(jobId)
      if (mountedRef.current) setResults(data)
    } catch (e) {
      if (mountedRef.current) setError(e.message)
    }
  }, [jobId])

  const handleUpdate = useCallback((update) => {
    if (!mountedRef.current) return
    if (update.ping) return
    if (update.error && !update.status) { setError(update.error); return }
    if (update.status) setStatus(update.status)
    if (update.progress !== undefined) setProgress(update.progress)
    if (update.message) setMessage(update.message)
    if (update.status === 'done') fetchResults()
    if (update.status === 'error') setError(update.error || 'Pipeline failed')
  }, [fetchResults])

  // Polling fallback in case WebSocket fails
  const startPolling = useCallback(() => {
    if (pollRef.current) return
    pollRef.current = setInterval(async () => {
      if (!mountedRef.current) return
      try {
        const s = await getJobStatus(jobId)
        handleUpdate({ status: s.status, progress: s.progress, message: s.status_message, error: s.error })
        if (s.status === 'done' || s.status === 'error') {
          clearInterval(pollRef.current)
          pollRef.current = null
        }
      } catch (e) {
        // ignore polling errors
      }
    }, 3000)
  }, [jobId, handleUpdate])

  useEffect(() => {
    if (!jobId) return
    mountedRef.current = true

    // Try WebSocket first
    let ws = null
    try {
      ws = connectJobWebSocket(jobId, (update) => {
        if (update.error && !update.status) {
          // WS failed — fall back to polling
          startPolling()
        } else {
          handleUpdate(update)
        }
      })
      ws.onerror = () => startPolling()
      ws.onclose = () => {
        if (mountedRef.current && status !== 'done' && status !== 'error') {
          startPolling()
        }
      }
      wsRef.current = ws
    } catch (e) {
      startPolling()
    }

    return () => {
      mountedRef.current = false
      if (wsRef.current) {
        wsRef.current.onmessage = null
        wsRef.current.onerror = null
        wsRef.current.onclose = null
        try { wsRef.current.close() } catch (e) {}
        wsRef.current = null
      }
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [jobId])

  return { status, progress, message, results, error }
}
