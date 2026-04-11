import { useCallback, useEffect, useState } from 'react'
import { getConversionResult, startConversion } from '@/api/client'
import type { ConversionOptions, ConversionProgress, ConversionResult } from '@/types/conversion'
import { useWebSocket } from './useWebSocket'

export type ConversionState = 'idle' | 'uploading' | 'converting' | 'completed' | 'failed'

export function useConversion() {
  const [state, setState] = useState<ConversionState>('idle')
  const [jobId, setJobId] = useState<string | null>(null)
  const [result, setResult] = useState<ConversionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { progress } = useWebSocket(jobId)

  // WebSocketの進捗状況を監視
  useEffect(() => {
    if (!progress) return

    if (progress.status === 'completed') {
      setState('completed')
      // 変換結果を取得
      getConversionResult(progress.jobId)
        .then(setResult)
        .catch((err: Error) => {
          setError(err.message)
          setState('failed')
        })
    } else if (progress.status === 'failed') {
      setState('failed')
      setError(progress.error ?? '変換中にエラーが発生しました')
    }
  }, [progress])

  const convert = useCallback(async (file: File, options: ConversionOptions) => {
    setState('uploading')
    setError(null)
    setResult(null)
    setJobId(null)

    try {
      const job = await startConversion(file, options)
      setJobId(job.jobId)
      setState('converting')
    } catch (err) {
      setState('failed')
      setError(err instanceof Error ? err.message : '変換の開始に失敗しました')
    }
  }, [])

  const reset = useCallback(() => {
    setState('idle')
    setJobId(null)
    setResult(null)
    setError(null)
  }, [])

  return {
    state,
    jobId,
    progress,
    result,
    error,
    convert,
    reset,
  }
}
