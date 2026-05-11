import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Crosshair, History, LogOut, Radar } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import clsx from 'clsx'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/analysis', icon: Crosshair, label: 'Analysis' },
  { to: '/history', icon: History, label: 'History' },
]

export default function Sidebar() {
  const logout = useAuthStore((s) => s.logout)
  const user = useAuthStore((s) => s.user)

  return (
    <aside
      className="w-[200px] flex flex-col border-r"
      style={{ background: 'rgba(6,13,20,0.95)', borderColor: 'var(--border)' }}
    >
      {/* Logo */}
      <div className="p-4 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2 mb-1">
          <div
            className="w-7 h-7 rounded flex items-center justify-center"
            style={{ background: 'rgba(0,255,136,0.1)', border: '1px solid var(--accent-dim)' }}
          >
            <Radar size={14} style={{ color: 'var(--accent)' }} />
          </div>
          <span
            className="font-hud font-black text-sm tracking-wider"
            style={{ color: 'var(--accent)' }}
          >
            AURIC<span style={{ color: 'var(--text-dim)', fontWeight: 400 }}>VISION</span>
          </span>
        </div>
        <div className="font-mono text-[0.55rem] tracking-widest uppercase" style={{ color: 'var(--muted)' }}>
          Defense Intelligence v1.0
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-2 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to}>
            {({ isActive }) => (
              <div
                className={clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded cursor-pointer transition-all duration-150',
                  isActive
                    ? 'text-accent'
                    : 'hover:text-text-primary'
                )}
                style={{
                  background: isActive ? 'rgba(0,255,136,0.06)' : 'transparent',
                  border: isActive ? '1px solid rgba(0,170,85,0.3)' : '1px solid transparent',
                  color: isActive ? 'var(--accent)' : 'var(--text-dim)',
                }}
              >
                <Icon size={14} />
                <span className="font-hud text-[0.62rem] tracking-widest uppercase">{label}</span>
              </div>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User + Logout */}
      <div className="p-3 border-t" style={{ borderColor: 'var(--border)' }}>
        {user && (
          <div className="mb-3 px-1">
            <div className="font-mono text-[0.65rem]" style={{ color: 'var(--text-primary)' }}>
              {user.full_name}
            </div>
            <div className="font-mono text-[0.58rem]" style={{ color: 'var(--muted)' }}>
              {user.role.toUpperCase()} · {user.clearance_level.toUpperCase()}
            </div>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-3 py-2 rounded transition-colors"
          style={{ color: 'var(--muted)', fontFamily: "'Orbitron', monospace", fontSize: '0.58rem', letterSpacing: '0.1em' }}
          onMouseOver={(e) => (e.currentTarget.style.color = 'var(--danger)')}
          onMouseOut={(e) => (e.currentTarget.style.color = 'var(--muted)')}
        >
          <LogOut size={13} />
          LOGOUT
        </button>
      </div>
    </aside>
  )
}
