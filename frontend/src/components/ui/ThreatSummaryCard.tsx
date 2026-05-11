import type { ThreatCounts } from '@/lib/types'

const LEVELS = [
  { key: 'critical' as const, label: 'CRITICAL', color: '#ff1a1a' },
  { key: 'high'     as const, label: 'HIGH',     color: '#ff6b00' },
  { key: 'medium'   as const, label: 'MEDIUM',   color: '#ffd700' },
  { key: 'low'      as const, label: 'LOW',       color: '#00ff88' },
]

export default function ThreatSummaryCard({ counts, compact = false }: { counts: ThreatCounts; compact?: boolean }) {
  return (
    <div className="grid grid-cols-4 gap-2">
      {LEVELS.map(({ key, label, color }) => (
        <div key={key} className="tac-card text-center" style={{ padding: compact ? '8px 4px' : '14px 8px' }}>
          <div className="font-hud font-black" style={{ fontSize: compact ? '1.4rem' : '2rem', color, textShadow: counts[key] > 0 ? `0 0 12px ${color}` : 'none' }}>
            {counts[key] ?? 0}
          </div>
          <div className="font-mono uppercase tracking-widest" style={{ fontSize: '0.52rem', color: 'var(--muted)', marginTop: 2 }}>
            {label}
          </div>
        </div>
      ))}
    </div>
  )
}
