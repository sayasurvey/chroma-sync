export interface ConversionOptions {
  targetSizeKb?: number
  quality: number
  maxDeltaE: number
}

export type ConversionStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface ConversionJob {
  jobId: string
  status: ConversionStatus
  createdAt: string
  completedAt?: string
  error?: string
  deltaE?: number
}

export interface ConversionProgress {
  jobId: string
  status: ConversionStatus
  progress: number
  message: string
  deltaE?: number
  error?: string
}

export interface Region {
  x: number
  y: number
  width: number
  height: number
  deltaEBefore: number
  deltaEAfter: number
}

export interface ConversionResult {
  jobId: string
  success: boolean
  originalSizeBytes: number
  outputSizeBytes: number
  deltaE: number
  correctionsApplied: boolean
  correctionRegionsCount: number
}

export type ItemState = 'idle' | 'uploading' | 'converting' | 'completed' | 'failed'

export interface FileConversionItem {
  id: string
  file: File
  state: ItemState
  jobId: string | null
  progress: ConversionProgress | null
  result: ConversionResult | null
  error: string | null
}
