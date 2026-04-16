import { useCallback, useEffect, useRef, useState } from 'react'
import type { ConversionProgress } from '@/types/conversion'

// Electron環境ではpreload.jsで注入されたベースURLを使用する
const WS_BASE = typeof window !== 'undefined'
  ? (window.__CHROMA_SYNC__?.apiBaseUrl
      ? window.__CHROMA_SYNC__.apiBaseUrl.replace(/^http/, 'ws')
      : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`)
  : 'ws://localhost:8000'

export function useWebSocket(jobId: string | null) {
  const [progress, setProgress] = useState<ConversionProgress | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const connect = useCallback((id: string) => {
    if (wsRef.current) {
      wsRef.current.close()
    }

    const ws = new WebSocket(`${WS_BASE}/ws/${id}`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setProgress({
          jobId: data.job_id,
          status: data.status,
          progress: data.progress ?? 0,
          message: data.message ?? '',
          deltaE: data.delta_e,
          error: data.error,
        })
      } catch {
        // JSONパースエラーは無視
      }
    }

    ws.onerror = () => {
      // WebSocket接続エラーはUIで処理
    }

    ws.onclose = () => {
      wsRef.current = null
    }
  }, [])

  useEffect(() => {
    if (jobId) {
      connect(jobId)
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [jobId, connect])

  return { progress }
}
