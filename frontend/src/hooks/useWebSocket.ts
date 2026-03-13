import { useEffect, useRef } from 'react'
import { WS_URL } from '../lib/api'
import { useLiveStore } from '../store/liveStore'
import type { WSTickPayload, WSInitPayload } from '../types'

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { setConnected, setError, applyTick, applyInit } = useLiveStore()

  useEffect(() => {
    let unmounted = false

    function connect() {
      if (unmounted) return
      try {
        const ws = new WebSocket(WS_URL)
        wsRef.current = ws

        ws.onopen = () => {
          if (!unmounted) setConnected(true)
        }

        ws.onmessage = (e: MessageEvent) => {
          if (unmounted) return
          try {
            const data = JSON.parse(e.data)
            if (data.type === 'init') applyInit(data as WSInitPayload)
            else if (data.type === 'tick') applyTick(data as WSTickPayload)
          } catch { /* ignore parse errors */ }
        }

        ws.onclose = () => {
          if (!unmounted) {
            setConnected(false)
            retryRef.current = setTimeout(connect, 3000)
          }
        }

        ws.onerror = () => {
          if (!unmounted) setError()
          ws.close()
        }
      } catch {
        if (!unmounted) {
          setError()
          retryRef.current = setTimeout(connect, 5000)
        }
      }
    }

    connect()

    return () => {
      unmounted = true
      if (retryRef.current) clearTimeout(retryRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [])
}
