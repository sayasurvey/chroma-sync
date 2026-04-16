import { useCallback, useRef, useState } from 'react'
import { getConversionResult, getJobStatus, startConversion } from '@/api/client'
import type { ConversionOptions, ConversionProgress, FileConversionItem } from '@/types/conversion'

export function useMultiConversion() {
  const [items, setItems] = useState<FileConversionItem[]>([])
  const pollingRefs = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map())

  const convertAll = useCallback(async (files: File[], options: ConversionOptions) => {
    pollingRefs.current.forEach(interval => clearInterval(interval))
    pollingRefs.current.clear()

    const newItems: FileConversionItem[] = files.map((file, index) => ({
      id: `${Date.now()}-${index}`,
      file,
      state: 'uploading',
      jobId: null,
      progress: null,
      result: null,
      error: null,
    }))
    setItems(newItems)

    newItems.forEach(async (item) => {
      try {
        const job = await startConversion(item.file, options)

        setItems(prev =>
          prev.map(i =>
            i.id === item.id
              ? {
                  ...i,
                  jobId: job.jobId,
                  state: 'converting',
                  progress: {
                    jobId: job.jobId,
                    status: 'pending',
                    progress: 5,
                    message: '変換処理を開始しています...',
                  } satisfies ConversionProgress,
                }
              : i
          )
        )

        const intervalId = setInterval(async () => {
          try {
            const status = await getJobStatus(job.jobId)
            const progress: ConversionProgress = {
              jobId: job.jobId,
              status: status.status,
              progress:
                status.status === 'completed' ? 100 : status.status === 'processing' ? 50 : 10,
              message:
                status.status === 'completed'
                  ? '変換完了'
                  : status.status === 'failed'
                    ? 'エラー'
                    : '変換処理中...',
              deltaE: status.deltaE,
              error: status.error,
            }

            if (status.status === 'completed') {
              clearInterval(intervalId)
              pollingRefs.current.delete(item.id)
              try {
                const result = await getConversionResult(job.jobId)
                setItems(prev =>
                  prev.map(i => (i.id === item.id ? { ...i, state: 'completed', progress, result } : i))
                )
              } catch (err) {
                setItems(prev =>
                  prev.map(i =>
                    i.id === item.id
                      ? {
                          ...i,
                          state: 'failed',
                          error: err instanceof Error ? err.message : '結果取得に失敗しました',
                        }
                      : i
                  )
                )
              }
            } else if (status.status === 'failed') {
              clearInterval(intervalId)
              pollingRefs.current.delete(item.id)
              setItems(prev =>
                prev.map(i =>
                  i.id === item.id
                    ? {
                        ...i,
                        state: 'failed',
                        progress,
                        error: status.error ?? '変換中にエラーが発生しました',
                      }
                    : i
                )
              )
            } else {
              setItems(prev => prev.map(i => (i.id === item.id ? { ...i, progress } : i)))
            }
          } catch {
            // polling error - ignore and retry
          }
        }, 1500)

        pollingRefs.current.set(item.id, intervalId)
      } catch (err) {
        setItems(prev =>
          prev.map(i =>
            i.id === item.id
              ? {
                  ...i,
                  state: 'failed',
                  error: err instanceof Error ? err.message : '変換の開始に失敗しました',
                }
              : i
          )
        )
      }
    })
  }, [])

  const reset = useCallback(() => {
    pollingRefs.current.forEach(interval => clearInterval(interval))
    pollingRefs.current.clear()
    setItems([])
  }, [])

  const isProcessing = items.some(item => item.state === 'uploading' || item.state === 'converting')
  const allDone =
    items.length > 0 && items.every(item => item.state === 'completed' || item.state === 'failed')

  return { items, convertAll, reset, isProcessing, allDone }
}
