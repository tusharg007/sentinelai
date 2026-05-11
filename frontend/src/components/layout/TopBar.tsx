import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type { HealthResult } from '@/lib/types'

export default function TopBar() {
  const [time, setTime] = useState('')

  useEffect(() => {
    const tick = () => {
      const now = new Date()
      const utc = now.toUTCString().match(/(\d{2}:\d{2}:\d{2})/)?.[1] ?? ''
      setTime(`${utc}Z`)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  const { data: health } = useQuery<HealthResult>({
    queryKey: ['health'],
    queryFn: () => api.get('/health').then((r) => r.data),
    refetchInterval: 10_000,
    retry: false,
  })

  const online = health?.status === 'operational'

  return (
    <div
      className="flex items-center justify-between px-5 h-11 border-b shrink-0"
      style={{ background: 'rgba(6,13,20,0.95)', borderColor: 'var(--border)' }}
    >
      {/* System tags */}
      <div className="flex items-center gap-3">
        <div
          className="px-2 py-0.5 font-hud text-[0.58rem] tracking-widest uppercase border rounded-sm"
          style={{
            borderColor: online ? 'rgba(0,255,136,0.4)' : 'rgba(255,26,26,0.4)',
            color: online ? 'var(--accent)' : 'var(--danger)',
            background: online ? 'rgba(0,255,136,0.04)' : 'rgba(255,26,26,0.04)',
          }}
        >
          SYS: {online ? 'ONLINE' : 'OFFLINE'}
        </div>
        {health && (
          <>
            <div className="font-mono text-[0.6rem]" style={{ color: 'var(--muted)' }}>
              DEVICE: <span style={{ color: 'var(--text-dim)' }}>{health.device.toUpperCase()}</span>
            </div>
            <div className="font-mono text-[0.6rem]" style={{ color: 'var(--muted)' }}>
              MODELS: <span style={{ color: 'var(--accent-dim)' }}>{health.loaded_models.join(' · ').toUpperCase()}</span>
            </div>
          </>
        )}
      </div>

      {/* Right */}
      <div className="flex items-center gap-4">
        {health?.db_connected !== undefined && (
          <div className="flex items-center gap-1.5 font-mono text-[0.6rem]" style={{ color: 'var(--muted)' }}>
            DB
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: health.db_connected ? 'var(--accent)' : 'var(--danger)' }}
            />
          </div>
        )}
        <div
          className="font-hud text-[0.72rem] tracking-widest"
          style={{ color: 'var(--accent)' }}
        >
          {time}
        </div>
      </div>
    </div>
  )
}
