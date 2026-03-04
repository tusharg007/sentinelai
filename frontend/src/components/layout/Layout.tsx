import { Outlet } from 'react-router-dom'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Crosshair, History, Radar } from 'lucide-react'
import { useState, useEffect } from 'react'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/analysis',  icon: Crosshair,       label: 'Analysis'  },
  { to: '/history',   icon: History,         label: 'History'   },
]

function Sidebar() {
  return (
    <div className="w-[200px] h-full flex flex-col border-r shrink-0 relative z-10"
      style={{ background: 'rgba(6,13,20,0.95)', borderColor: 'var(--border)' }}>
      {/* Logo */}
      <div className="p-4 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2">
          <Radar size={18} style={{ color: 'var(--accent)' }} className="radar-sweep" />
          <div>
            <div className="font-hud font-black text-[0.75rem] tracking-widest"
              style={{ color: 'var(--accent)', textShadow: '0 0 10px rgba(0,255,136,0.4)' }}>
              SENTINELAI
            </div>
            <div className="font-mono text-[0.48rem] tracking-widest" style={{ color: 'var(--muted)' }}>
              BATTLEFIELD INTEL
            </div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded text-[0.68rem] font-mono transition-all ${
                isActive ? 'text-accent' : ''
              }`
            }
            style={({ isActive }) => ({
              background: isActive ? 'rgba(0,255,136,0.07)' : 'transparent',
              color: isActive ? 'var(--accent)' : 'var(--text-dim)',
              borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
            })}>
            <Icon size={13} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t" style={{ borderColor: 'var(--border)' }}>
        <div className="font-mono text-[0.53rem] text-center" style={{ color: 'var(--muted)' }}>
          CLASSIFIED · AUTHORIZED USE ONLY
        </div>
      </div>
    </div>
  )
}

function TopBar() {
  const [time, setTime] = useState('')
  useEffect(() => {
    const tick = () => setTime(new Date().toUTCString().slice(17, 25) + ' UTC')
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="h-10 border-b flex items-center justify-between px-4 shrink-0 relative z-10"
      style={{ background: 'rgba(6,13,20,0.95)', borderColor: 'var(--border)' }}>
      <div className="flex items-center gap-4 font-mono text-[0.6rem]">
        <span className="font-hud tracking-widest" style={{ color: 'var(--accent)' }}>SENTINELAI</span>
        <span style={{ color: 'var(--muted)' }}>/ BATTLEFIELD INTELLIGENCE v1.0</span>
      </div>
      <div className="flex items-center gap-4 font-mono text-[0.6rem]">
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--accent)', boxShadow: '0 0 4px var(--accent)' }} />
          <span style={{ color: 'var(--accent)' }}>ONLINE</span>
        </div>
        <span style={{ color: 'var(--muted)' }}>{time}</span>
      </div>
    </div>
  )
}

export default function Layout() {
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <TopBar />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto relative z-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
