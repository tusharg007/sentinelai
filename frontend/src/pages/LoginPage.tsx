import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/auth'

export default function LoginPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const { login, register } = useAuthStore()
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')

  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  const mutation = useMutation({
    mutationFn: async () => {
      if (isRegister) await register(email, password, fullName)
      else await login(email, password)
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? 'Authentication failed')
    },
  })

  return (
    <div className="relative z-10 min-h-screen flex items-center justify-center">
      {/* Large tactical circle background */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {[300, 500, 700].map((size) => (
          <div
            key={size}
            className="absolute rounded-full border"
            style={{
              width: size, height: size,
              borderColor: 'rgba(0,255,136,0.04)',
            }}
          />
        ))}
      </div>

      <div className="w-full max-w-sm px-4">
        {/* Header */}
        <div className="text-center mb-10">
          <div
            className="font-hud font-black text-3xl tracking-widest mb-2"
            style={{ color: 'var(--accent)', textShadow: '0 0 30px rgba(0,255,136,0.4)' }}
          >
            AURICVISION
          </div>
          <div className="font-mono text-[0.65rem] tracking-widest uppercase" style={{ color: 'var(--muted)' }}>
            Defense Intelligence Platform
          </div>
          <div className="w-16 h-px mx-auto mt-3" style={{ background: 'var(--accent-dim)' }} />
        </div>

        {/* Card */}
        <div
          className="rounded p-8"
          style={{
            background: 'rgba(6,13,20,0.9)',
            border: '1px solid var(--border)',
            backdropFilter: 'blur(12px)',
          }}
        >
          <div className="font-hud text-[0.65rem] tracking-widest uppercase mb-6" style={{ color: 'var(--accent)' }}>
            {isRegister ? '◈ REGISTER OPERATOR' : '◈ OPERATOR AUTHENTICATION'}
          </div>

          <div className="space-y-4">
            {isRegister && (
              <div>
                <label className="block font-hud text-[0.55rem] tracking-widest uppercase mb-1.5" style={{ color: 'var(--muted)' }}>
                  Full Name
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="tac-input"
                  placeholder="Enter full name"
                />
              </div>
            )}

            <div>
              <label className="block font-hud text-[0.55rem] tracking-widest uppercase mb-1.5" style={{ color: 'var(--muted)' }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && mutation.mutate()}
                className="tac-input"
                placeholder="operator@auric.mil"
              />
            </div>

            <div>
              <label className="block font-hud text-[0.55rem] tracking-widest uppercase mb-1.5" style={{ color: 'var(--muted)' }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && mutation.mutate()}
                className="tac-input"
                placeholder="••••••••••"
              />
            </div>

            <button
              className={`tac-btn w-full mt-2 ${mutation.isPending ? 'running' : ''}`}
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending || !email || !password}
            >
              {mutation.isPending
                ? '◌ AUTHENTICATING...'
                : isRegister ? '◈ CREATE ACCOUNT' : '◈ AUTHENTICATE'}
            </button>
          </div>

          <button
            onClick={() => setIsRegister(!isRegister)}
            className="w-full mt-4 font-mono text-[0.62rem] underline-offset-2 hover:underline"
            style={{ color: 'var(--muted)' }}
          >
            {isRegister ? 'Already have an account? Login' : 'New operator? Register'}
          </button>
        </div>

        <div className="mt-6 text-center font-mono text-[0.58rem]" style={{ color: 'var(--muted)' }}>
          CLASSIFIED SYSTEM · AUTHORIZED USERS ONLY
        </div>
      </div>
    </div>
  )
}
