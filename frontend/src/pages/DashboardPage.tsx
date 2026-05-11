import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Activity, Crosshair, Clock, TrendingUp, Zap } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import api from '@/lib/api'
import type { HealthResult } from '@/lib/types'

const CAPABILITIES = [
  { title: 'Military Asset Detection',  desc: 'YOLOv8 + military taxonomy — tanks, radar, aircraft, ships, missile launchers', badge: 'YOLOv8' },
  { title: 'Multi-Modal Fusion',         desc: 'Channel-attention EO + IR + SAR fusion — all-condition ISR', badge: 'EO/IR/SAR' },
  { title: 'Temporal Change Detection', desc: 'CLIP ViT-B/32 Siamese change detection between satellite passes', badge: 'ViT' },
  { title: 'Geospatial Targeting',       desc: 'Pixel → WGS84 + MGRS grid with GSD-aware footprint estimation', badge: 'GPS/MGRS' },
  { title: 'Threat Prioritization',      desc: 'Multi-factor scoring: base × confidence × proximity × operator × mission', badge: 'AI' },
  { title: 'Defense Data Pipeline',      desc: 'DOTA/DIOR OBB parser + camouflage/haze/SAR-speckle augmentation', badge: 'DOTA' },
]

export default function DashboardPage() {
  const user     = useAuthStore(s => s.user)
  const navigate = useNavigate()

  const { data: health } = useQuery<HealthResult>({
    queryKey: ['health'],
    queryFn: () => api.get('/health').then(r => r.data),
    refetchInterval: 15_000,
    retry: false,
  })

  const online = health?.status === 'operational'

  return (
    <div className="p-6 max-w-5xl mx-auto relative z-10">

      {/* Header */}
      <div className="mb-8">
        <div className="font-hud font-black text-2xl tracking-wider mb-1" style={{ color: 'var(--accent)', textShadow: '0 0 24px rgba(0,255,136,0.3)' }}>
          AURICVISION
          <span className="ml-3 font-normal text-sm tracking-widest" style={{ color: 'var(--muted)' }}>INTELLIGENCE PLATFORM</span>
        </div>
        {user && (
          <div className="font-mono text-[0.7rem]" style={{ color: 'var(--text-dim)' }}>
            {user.full_name} · {user.clearance_level.toUpperCase()} · {user.role.toUpperCase()}
          </div>
        )}
      </div>

      {/* System status */}
      {health && (
        <div className="tac-card p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full" style={{ background: online ? 'var(--accent)' : 'var(--danger)', boxShadow: `0 0 6px ${online ? 'var(--accent)' : 'var(--danger)'}` }} />
              <span className="font-hud text-[0.63rem] tracking-widest" style={{ color: online ? 'var(--accent)' : 'var(--danger)' }}>
                SYSTEM {health.status.toUpperCase()}
              </span>
            </div>
            <div className="flex gap-5 font-mono text-[0.6rem]">
              {[
                ['DEVICE',  health.device.toUpperCase()],
                ['TORCH',   health.torch],
                ['PYTHON',  health.python],
                ['MODELS',  health.loaded_models.join(' · ') || 'none'],
              ].map(([k,v]) => (
                <div key={k}>
                  <span style={{ color: 'var(--muted)' }}>{k}: </span>
                  <span style={{ color: 'var(--text-dim)' }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-3 mb-8">
        {[
          { label: 'ANALYSES', value: '—', icon: Activity,   color: '#00ff88' },
          { label: 'TARGETS',  value: '—', icon: Crosshair,  color: '#ff6b00' },
          { label: 'AVG MS',   value: '—', icon: Clock,      color: '#ffd700' },
          { label: 'mAP',      value: '71%', icon: TrendingUp, color: '#00b4ff' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="tac-card p-4">
            <div className="flex items-center justify-between mb-2">
              <Icon size={14} style={{ color }} />
              <span className="font-mono text-[0.53rem] tracking-wider" style={{ color: 'var(--muted)' }}>{label}</span>
            </div>
            <div className="font-hud font-black text-2xl" style={{ color }}>{value}</div>
          </div>
        ))}
      </div>

      {/* CTA */}
      <div className="rounded p-6 mb-8 relative overflow-hidden" style={{ background: 'rgba(0,255,136,0.03)', border: '1px solid rgba(0,255,136,0.15)' }}>
        <div className="absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl opacity-10" style={{ background: 'var(--accent)', transform: 'translate(20%,-20%)' }} />
        <div className="font-hud text-[0.63rem] tracking-widest uppercase mb-1" style={{ color: 'var(--accent)' }}>Ready for Intelligence Analysis</div>
        <div className="font-mono text-[0.7rem] mb-4" style={{ color: 'var(--text-dim)' }}>
          Upload satellite or drone imagery to detect, geolocate, and prioritize military assets in real time.
        </div>
        <button className="tac-btn" onClick={() => navigate('/analysis')}>
          <Zap size={13} /> BEGIN ANALYSIS
        </button>
      </div>

      {/* Capabilities */}
      <div className="section-header font-hud text-[0.6rem] tracking-widest uppercase mb-4" style={{ color: 'var(--accent)' }}>Platform Capabilities</div>
      <div className="grid grid-cols-2 gap-3">
        {CAPABILITIES.map(({ title, desc, badge }) => (
          <div key={title} className="tac-card p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="font-hud text-[0.63rem] tracking-wider" style={{ color: 'var(--text-primary)' }}>{title}</div>
              <span className="font-hud text-[0.48rem] px-2 py-0.5 rounded-sm border tracking-widest"
                style={{ borderColor: 'var(--accent-dim)', color: 'var(--accent)', background: 'rgba(0,255,136,0.05)' }}>{badge}</span>
            </div>
            <div className="font-mono text-[0.61rem] leading-relaxed" style={{ color: 'var(--text-dim)' }}>{desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
