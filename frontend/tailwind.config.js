/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0a0f',
        surface: '#111118',
        card: '#16161f',
        border: '#1e1e2e',
        accent: '#6366f1',
        'accent-light': '#818cf8',
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#ef4444',
        muted: '#4b5563',
        text: '#e2e8f0',
        'text-muted': '#64748b',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'Inter', 'sans-serif'],
        mono: ['SF Mono', 'JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        xl: '1rem',
        '2xl': '1.25rem',
      },
      boxShadow: {
        card: '0 0 0 1px rgba(255,255,255,0.05), 0 4px 24px rgba(0,0,0,0.4)',
        glow: '0 0 20px rgba(99,102,241,0.3)',
      },
    },
  },
  plugins: [],
}
