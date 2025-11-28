import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useCallback, useRef, useEffect } from 'react'
import type { Message, Job, CreateJobResponse, AppConfig, ToolCall, JobProgress } from './types'

const API_URL = import.meta.env.VITE_API_URL || '/api'

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)
  if (!response.ok) throw new Error(`API error: ${response.status}`)
  return response.json()
}

export function useConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: () => fetchJson<AppConfig>(`${API_URL}/config`),
    staleTime: Infinity,
  })
}

async function createJob(query: string, history: Message[]): Promise<CreateJobResponse> {
  return fetchJson(`${API_URL}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, history }),
  })
}

async function getJob(jobId: string): Promise<Job> {
  return fetchJson(`${API_URL}/jobs/${jobId}`)
}

export function useChat() {
  const queryClient = useQueryClient()
  const [jobId, setJobId] = useState<string | null>(null)
  const [allToolTraces, setAllToolTraces] = useState<ToolCall[]>([])
  const [progress, setProgress] = useState<JobProgress | null>(null)
  const lastTraceLength = useRef(0)

  const jobQuery = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const job = query.state.data
      if (!job) return 500
      if (job.status === 'completed' || job.status === 'failed') return false
      return 500
    },
  })

  const job = jobQuery.data

  useEffect(() => {
    if (!job?.tool_trace) return
    
    const newTrace = job.tool_trace
    if (newTrace.length > lastTraceLength.current) {
      const newTools = newTrace.slice(lastTraceLength.current)
      setAllToolTraces(prev => [...newTools, ...prev])
      lastTraceLength.current = newTrace.length
    }
  }, [job?.tool_trace])

  useEffect(() => {
    if (job?.progress) {
      setProgress(job.progress)
    }
  }, [job?.progress])

  const submitMutation = useMutation({
    mutationFn: ({ query, history }: { query: string; history: Message[] }) => 
      createJob(query, history),
    onSuccess: (data) => {
      setJobId(data.job_id)
      lastTraceLength.current = 0
      setProgress(null)
    },
  })

  const submit = useCallback((query: string, history: Message[]) => {
    submitMutation.mutate({ query, history })
  }, [submitMutation])

  const reset = useCallback(() => {
    setJobId(null)
    setProgress(null)
    lastTraceLength.current = 0
    queryClient.removeQueries({ queryKey: ['job'] })
  }, [queryClient])

  const clearHistory = useCallback(() => {
    setAllToolTraces([])
    lastTraceLength.current = 0
  }, [])

  const isLoading = submitMutation.isPending || (!!jobId && job?.status !== 'completed' && job?.status !== 'failed')
  const isComplete = job?.status === 'completed'
  const error = submitMutation.error?.message || (job?.status === 'failed' ? job.error : null)

  return {
    submit,
    reset,
    clearHistory,
    isLoading,
    isComplete,
    error,
    response: job?.response ?? null,
    toolTrace: allToolTraces,
    progress,
  }
}

interface UploadUrlResponse {
  url: string
  s3_path: string
  key: string
  content_type: string
  expires_in: number
  original_filename: string
}

async function getUploadUrl(filename: string, contentType?: string): Promise<UploadUrlResponse> {
  return fetchJson(`${API_URL}/documents/upload-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, content_type: contentType }),
  })
}

async function uploadToS3(url: string, file: File, contentType: string): Promise<void> {
  const response = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': contentType },
    body: file,
  })
  if (!response.ok) throw new Error(`S3 upload failed: ${response.status}`)
}

export function useUpload(onSuccess: (s3Path: string) => void) {
  return useMutation({
    mutationFn: async (file: File) => {
      const { url, s3_path, content_type } = await getUploadUrl(file.name, file.type || undefined)
      await uploadToS3(url, file, content_type)
      return s3_path
    },
    onSuccess,
  })
}

// Document View
interface ViewUrlResponse {
  url: string
  s3_path: string
  filename: string
  expires_in: number
}

export function useViewUrl() {
  return useMutation({
    mutationFn: (s3Path: string) => 
      fetchJson<ViewUrlResponse>(`${API_URL}/documents/view-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ s3_path: s3Path }),
      }),
  })
}
