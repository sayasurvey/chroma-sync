import { useCallback, useEffect, useRef, useState } from 'react'
import { getConversionResult, getJobStatus, startConversion } from '@/api/client'
import type { ConversionOptions, ConversionProgress, ConversionResult } from '@/types/conversion'

export type ConversionState = 'idle' | 'uploading' | 'converting' | 'completed' | 'failed'

export function useConversion() {
  const [state, setState] = useState<ConversionState>('idle')
  const [jobId, setJobId] = useState<string | null>(null)
  const [result, setResult] = useState<ConversionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<ConversionProgress | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const completedRef = useRef(false)

  const finishJob = useCallback((id: string) => {
    if (completedRef.current) return
    completedRef.current = true
    setState('completed')
    getConversionResult(id)
      .then(setResult)
      .catch((err: Error) => {
        setError(err.message)
        setState('failed')
      })
  }, [])

  // ジョブIDが設定されたらポーリング開始
  useEffect(() => {
    if (state !== 'converting' || !jobId) return

    pollingRef.current = setInterval(async () => {
      if (completedRef.current) {
        clearInterval(pollingRef.current!)
        return
      }
      try {
        const job = await getJobStatus(jobId)
        setProgress({
          jobId: job.jobId,
          status: job.status,
          progress: job.status === 'completed' ? 100 : job.status === 'processing' ? 50 : 10,
          message:
            job.status === 'completed'
              ? '変換完了'
              : job.status === 'failed'
                ? 'エラー'
                : '変換処理中...',
          deltaE: job.deltaE,
          error: job.error,
        })
        if (job.status === 'completed') {
          clearInterval(pollingRef.current!)
          finishJob(jobId)
        } else if (job.status === 'failed') {
          clearInterval(pollingRef.current!)
          if (!completedRef.current) {
            completedRef.current = true
            setState('failed')
            setError(job.error ?? '変換中にエラーが発生しました')
          }
        }
      } catch {
        // ポーリングエラーは無視して再試行
      }
    }, 2000)

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [state, jobId, finishJob])

  const convert = useCallback(async (file: File, options: ConversionOptions) => {
    setState('uploading')
    setError(null)
    setResult(null)
    setJobId(null)
    setProgress(null)
    completedRef.current = false

    setProgress({
      jobId: '',
      status: 'pending',
      progress: 0,
      message: 'ファイルをアップロード中...',
    })

    try {
      const job = await startConversion(file, options)
      setJobId(job.jobId)
      setState('converting')
      setProgress({
        jobId: job.jobId,
        status: 'pending',
        progress: 5,
        message: '変換処理を開始しています...',
      })
    } catch (err) {
      setState('failed')
      setError(err instanceof Error ? err.message : '変換の開始に失敗しました')
      setProgress(null)
    }
  }, [])

  const reset = useCallback(() => {
    setState('idle')
    setJobId(null)
    setResult(null)
    setError(null)
    setProgress(null)
    completedRef.current = false
    if (pollingRef.current) clearInterval(pollingRef.current)
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
