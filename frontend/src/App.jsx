import { useState } from 'react'
import UploadZone from './components/UploadZone'
import PipelineProgress from './components/PipelineProgress'
import Dashboard from './pages/Dashboard'
import { useJob } from './hooks/useJob'

function JobView({ jobId, filename, preprocess, onReset }) {
  const { status, progress, message, results, error } = useJob(jobId)
  if (status === 'done' && results)
    return <Dashboard results={results} filename={filename} onReset={onReset} />
  return (
    <PipelineProgress
      filename={filename} status={status} progress={progress}
      message={message} error={error} preprocess={preprocess}
    />
  )
}

export default function App() {
  const [job, setJob] = useState(null)
  const handleJobCreated = (jobId, filename, preprocess) =>
    setJob({ jobId, filename, preprocess })
  const handleReset = () => setJob(null)

  if (!job) return <UploadZone onJobCreated={handleJobCreated} />
  return (
    <JobView jobId={job.jobId} filename={job.filename}
             preprocess={job.preprocess} onReset={handleReset} />
  )
}
