import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '@/lib/api'

interface User { id: string; email: string; full_name: string; role: string; clearance_level: string }

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null, accessToken: null, refreshToken: null, isAuthenticated: false,

      login: async (email, password) => {
        const { data } = await api.post('/auth/login', { email, password })
        set({ accessToken: data.access_token, refreshToken: data.refresh_token, isAuthenticated: true })
        const { data: user } = await api.get('/auth/me')
        set({ user })
      },

      register: async (email, password, fullName) => {
        await api.post('/auth/register', { email, password, full_name: fullName })
        await get().login(email, password)
      },

      logout: () => set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false }),
    }),
    {
      name: 'auricvision-auth',
      partialize: s => ({ accessToken: s.accessToken, refreshToken: s.refreshToken, isAuthenticated: s.isAuthenticated, user: s.user }),
    }
  )
)
