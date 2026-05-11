import { Clock } from 'lucide-react'

export default function HistoryPage() {
  return (
    <div className="p-6 relative z-10">
      <div className="font-hud text-[0.65rem] tracking-widest uppercase mb-6" style={{ color: 'var(--accent)' }}>
        ◈ Analysis History
      </div>
      <div className="tac-card p-12 flex flex-col items-center gap-4">
        <Clock size={28} style={{ color: 'var(--muted)' }} />
        <div className="font-hud text-[0.65rem] tracking-wider" style={{ color: 'var(--text-dim)' }}>
          HISTORY MODULE
        </div>
        <div className="font-mono text-[0.65rem] text-center max-w-sm" style={{ color: 'var(--muted)' }}>
          Analysis history is stored in PostgreSQL and retrieved via the{' '}
          <code style={{ color: 'var(--accent-dim)' }}>GET /api/v1/analyses</code> endpoint.
          Implement this page by connecting the query to the API.
        </div>
      </div>
    </div>
  )
}
