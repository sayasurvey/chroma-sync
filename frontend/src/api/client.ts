import type { ConversionJob, ConversionOptions, ConversionResult } from '@/types/conversion'

// Electron環境ではpreload.jsで注入されたベースURLを使用する。
// Vite開発環境ではプロキシ経由で /api を使用する。
declare global {
  interface Window {
    __CHROMA_SYNC__?: { apiBaseUrl: string }
  }
}
const API_BASE = (window.__CHROMA_SYNC__?.apiBaseUrl ?? '') + '/api'

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'ネットワークエラーが発生しました' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

// API Gateway の 10MB ペイロード制限を考慮して 8MB 超は presigned URL フローを使用
const DIRECT_UPLOAD_LIMIT = 8 * 1024 * 1024

async function uploadViaPresignedUrl(
  file: File,
  options: ConversionOptions
): Promise<ConversionJob> {
  // Step 1: presigned URL を取得
  const presignFormData = new FormData()
  presignFormData.append('filename', file.name)
  const presignRes = await fetch(`${API_BASE}/presign-upload`, {
    method: 'POST',
    body: presignFormData,
  })
  const { upload_url, s3_key } = await handleResponse<{
    upload_url: string
    s3_key: string
    job_id: string
  }>(presignRes)

  // Step 2: S3 に直接 PUT アップロード
  const putRes = await fetch(upload_url, {
    method: 'PUT',
    body: file,
    headers: { 'Content-Type': 'application/octet-stream' },
  })
  if (!putRes.ok) {
    throw new Error(`S3 アップロードに失敗しました: HTTP ${putRes.status}`)
  }

  // Step 3: 変換ジョブを開始
  const convertFormData = new FormData()
  convertFormData.append('s3_key', s3_key)
  convertFormData.append('original_filename', file.name)
  if (options.targetSizeKb) {
    convertFormData.append('target_size_kb', String(options.targetSizeKb))
  }
  convertFormData.append('quality', String(options.quality))
  convertFormData.append('max_delta_e', String(options.maxDeltaE))

  const convertRes = await fetch(`${API_BASE}/convert`, {
    method: 'POST',
    body: convertFormData,
  })
  const data = await handleResponse<{ job_id: string; status: string }>(convertRes)
  return {
    jobId: data.job_id,
    status: data.status as ConversionJob['status'],
    createdAt: new Date().toISOString(),
  }
}

export async function startConversion(
  file: File,
  options: ConversionOptions
): Promise<ConversionJob> {
  // 8MB 超のファイルは presigned URL 経由でアップロード（API Gateway 10MB 制限回避）
  if (file.size > DIRECT_UPLOAD_LIMIT) {
    return uploadViaPresignedUrl(file, options)
  }

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
