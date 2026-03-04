/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#020507',
        surface: '#060d14',
        card: '#080f18',
        border: '#0e2233',
        accent: '#00ff88',
        'accent-dim': '#00aa55',
        warn: '#ff6b00',
        danger: '#ff1a1a',
        info: '#00b4ff',
        gold: '#ffd700',
        muted: '#3a6080',
        'text-primary': '#c8dde8',
        'text-dim': '#4a7090',
      },
      fontFamily: {
        hud: ['Orbitron', 'monospace'],
        data: ['IBM Plex Mono', 'monospace'],
        mono: ['Share Tech Mono', 'monospace'],
      },
      animation: {
        'radar-spin': 'radar-spin 3s linear infinite',
        blink: 'blink 1.5s ease-in-out infinite',
        'slide-in': 'slideIn 0.3s ease forwards',
        'fade-in': 'fadeIn 0.4s ease forwards',
        'pulse-warn': 'pulseWarn 1s ease infinite',
      },
      keyframes: {
        'radar-spin': { to: { transform: 'rotate(360deg)' } },
        blink: { '0%,100%': { opacity: '1' }, '50%': { opacity: '0.25' } },
        slideIn: { from: { opacity: '0', transform: 'translateX(12px)' }, to: { opacity: '1', transform: 'none' } },
        fadeIn: { from: { opacity: '0' }, to: { opacity: '1' } },
        pulseWarn: { '0%,100%': { opacity: '1' }, '50%': { opacity: '0.45' } },
      },
    },
  },
  plugins: [],
}
