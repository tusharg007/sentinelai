import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120_000,
})

// Inject JWT
api.interceptors.request.use((config) => {
  try {
    const raw = localStorage.getItem('auricvision-auth')
    if (raw) {
      const { state } = JSON.parse(raw)
      if (state?.accessToken) config.headers.Authorization = `Bearer ${state.accessToken}`
    }
  } catch { /* ignore */ }
  return config
})

// Auto-refresh on 401
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const orig = err.config
    if (err.response?.status === 401 && !orig._retry) {
      orig._retry = true
      try {
        const raw = localStorage.getItem('auricvision-auth')
        if (raw) {
          const parsed = JSON.parse(raw)
          const rt = parsed?.state?.refreshToken
          if (rt) {
            const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: rt })
            parsed.state.accessToken = data.access_token
            parsed.state.refreshToken = data.refresh_token
            localStorage.setItem('auricvision-auth', JSON.stringify(parsed))
            orig.headers.Authorization = `Bearer ${data.access_token}`
            return api(orig)
          }
        }
      } catch { /* fall through */ }
      localStorage.removeItem('auricvision-auth')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
