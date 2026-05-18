/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],

  darkMode: 'class',

  theme: {
    extend: {
      colors: {
        ide: {
          bg: '#0d1117',
          surface: '#161b22',
          elevated: '#21262d',
          border: '#30363d',
          'border-sub': '#21262d',

          text: '#e6edf3',
          muted: '#8b949e',
          dim: '#484f58',

          blue: '#388bfd',
          'blue-dim': '#1f3a5f',

          green: '#3fb950',
          'green-dim': '#1a3a22',

          purple: '#d2a8ff',
          'purple-dim': '#2d1f4a',

          amber: '#d29922',
          'amber-dim': '#3a2800',

          red: '#f85149',
          'red-dim': '#3a1616',

          teal: '#39c5cf',
          'teal-dim': '#0d2e30',
        },
      },

      fontFamily: {
        mono: [
          '"JetBrains Mono"',
          '"Fira Code"',
          '"Cascadia Code"',
          'monospace',
        ],

        sans: [
          '"Inter"',
          'system-ui',
          'sans-serif',
        ],
      },

      fontSize: {
        '2xs': ['0.65rem', { lineHeight: '1rem' }],
      },

      animation: {
        'slide-in-right': 'slideInRight 0.2s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
        'fade-in': 'fadeIn 0.15s ease-out',
        'spin-slow': 'spin 2s linear infinite',
      },

      keyframes: {
        slideInRight: {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },

        slideUp: {
          from: {
            transform: 'translateY(8px)',
            opacity: 0,
          },

          to: {
            transform: 'translateY(0)',
            opacity: 1,
          },
        },

        fadeIn: {
          from: { opacity: 0 },
          to: { opacity: 1 },
        },
      },
    },
  },

  plugins: [],
}