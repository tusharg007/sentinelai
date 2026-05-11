import type { DetectedAsset } from '@/lib/types'

const LEVEL_COLOR: Record<string, string> = {
  critical: '#ff1a1a', high: '#ff6b00', medium: '#ffd700', low: '#00ff88',
}

export default function TargetCard({ asset, index }: { asset: DetectedAsset; index: number }) {
  const color = LEVEL_COLOR[asset.threat_level] ?? '#00ff88'
  const displayScore = asset.final_score ?? asset.threat_score

  return (
    <div className="tac-card p-3 animate-slide-in"
      style={{ animationDelay: `${index * 40}ms`, borderLeftColor: color, borderLeftWidth: 2 }}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="font-hud text-[0.56rem] tracking-widest" style={{ color: 'var(--muted)' }}>
            {asset.asset_id}{asset.rank ? ` · RANK #${asset.rank}` : ''}
          </div>
          <div className="font-mono text-[0.76rem] font-semibold mt-0.5" style={{ color: 'var(--text-primary)' }}>
            {asset.military_class.replace(/_/g, ' ').toUpperCase()}
          </div>
        </div>
        <div className="text-right">
          <div className="font-hud font-black text-lg" style={{ color, textShadow: `0 0 8px ${color}` }}>
            {displayScore.toFixed(1)}
          </div>
          <span className={`badge badge-${asset.threat_level}`}>{asset.threat_level}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[0.6rem] font-mono mb-2">
        <div><span style={{ color: 'var(--muted)' }}>CONF: </span><span style={{ color: 'var(--accent-dim)' }}>{(asset.confidence * 100).toFixed(0)}%</span></div>
        <div><span style={{ color: 'var(--muted)' }}>TYPE: </span><span style={{ color: 'var(--text-dim)' }}>{asset.raw_class}</span></div>
      </div>

      {asset.coord_str && (
        <div className="text-[0.57rem] font-mono px-2 py-1 rounded mb-2"
          style={{ background: 'rgba(0,255,136,0.03)', border: '1px solid rgba(0,255,136,0.1)', color: 'var(--accent-dim)' }}>
          📍 {asset.coord_str}
          {asset.mgrs && <><br /><span style={{ color: 'var(--muted)' }}>MGRS: {asset.mgrs}</span></>}
          {asset.footprint_m2 && <><br /><span style={{ color: 'var(--muted)' }}>AREA: {asset.footprint_m2} m²</span></>}
        </div>
      )}

      {asset.action && (
        <div className="text-[0.57rem] font-mono pt-1.5" style={{ borderTop: '1px solid var(--border)', color: 'var(--warn)' }}>
          ▶ {asset.action}
        </div>
      )}
    </div>
  )
}
