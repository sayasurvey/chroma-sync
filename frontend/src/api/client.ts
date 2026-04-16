import type { ConversionJob, ConversionOptions, ConversionResult } from '@/types/conversion'

const API_BASE = '/api'

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'ネットワークエラーが発生しました' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export async function startConversion(
  file: File,
  options: ConversionOptions
): Promise<ConversionJob> {
  const formData = new FormData()
  formData.append('file', file)
  if (options.targetSizeKb) {
    formData.append('target_size_kb', String(options.targetSizeKb))
  }
  formData.append('quality', String(options.quality))
  formData.append('max_delta_e', String(options.maxDeltaE))

  const response = await fetch(`${API_BASE}/convert`, {
    method: 'POST',
    body: formData,
  })

  const data = await handleResponse<{ job_id: string; status: string }>(response)
  return {
    jobId: data.job_id,
    status: data.status as ConversionJob['status'],
    createdAt: new Date().toISOString(),
  }
}

export async function getJobStatus(jobId: string): Promise<ConversionJob> {
  const response = await fetch(`${API_BASE}/convert/${jobId}/status`)
  const data = await handleResponse<{
    job_id: string
    status: string
    created_at: string
    completed_at?: string
    error?: string
    delta_e?: number
  }>(response)

  return {
    jobId: data.job_id,
    status: data.status as ConversionJob['status'],
    createdAt: data.created_at,
    completedAt: data.completed_at,
    error: data.error,
    deltaE: data.delta_e,
  }
}

export async function getConversionResult(jobId: string): Promise<ConversionResult> {
  const response = await fetch(`${API_BASE}/convert/${jobId}/result`)
  const data = await handleResponse<{
    job_id: string
    success: boolean
    original_size_bytes: number
    output_size_bytes: number
    delta_e: number
    corrections_applied: boolean
    correction_regions_count: number
  }>(response)

  return {
    jobId: data.job_id,
    success: data.success,
    originalSizeBytes: data.original_size_bytes,
    outputSizeBytes: data.output_size_bytes,
    deltaE: data.delta_e,
    correctionsApplied: data.corrections_applied,
    correctionRegionsCount: data.correction_regions_count,
  }
}

export function getDownloadUrl(jobId: string): string {
  return `${API_BASE}/convert/${jobId}/download`
}

export function getPreviewUrl(jobId: string): string {
  return `${API_BASE}/convert/${jobId}/preview`
}

export function getBatchDownloadUrl(jobIds: string[]): string {
  const params = jobIds.map(id => `job_ids=${encodeURIComponent(id)}`).join('&')
  return `${API_BASE}/convert/batch-download?${params}`
}
