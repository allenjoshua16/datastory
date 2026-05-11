import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''

export const api = axios.create({ baseURL: BASE })

export async function uploadDataset(file, audience = 'executive') {
  const form = new FormData()
  form.append('file', file)
  form.append('audience', audience)
  const { data } = await api.post('/api/upload', form)
  return data // { job_id, filename, message }
}

export async function getJobStatus(jobId) {
  const { data } = await api.get(`/api/jobs/${jobId}/status`)
  return data
}

export async function getJobResults(jobId) {
  const { data } = await api.get(`/api/jobs/${jobId}/results`)
  return data
}

export function connectJobWebSocket(jobId, onUpdate) {
  const wsBase = (import.meta.env.VITE_API_URL || window.location.origin)
    .replace(/^http/, 'ws')
  const ws = new WebSocket(`${wsBase}/api/ws/${jobId}`)
  ws.onmessage = (e) => onUpdate(JSON.parse(e.data))
  ws.onerror = () => onUpdate({ error: 'WebSocket error' })
  return ws
}
