/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Dark clinical surface scale
        ink: {
          950: '#0a0b0c',
          900: '#0d0e10',
          850: '#121316',
          800: '#16171a',
          750: '#1c1d21',
          700: '#232429',
          600: '#2c2d33',
        },
        line: 'rgba(255,255,255,0.08)',
        brand: {
          DEFAULT: '#34d399',
          fg: '#4ade80',
          soft: 'rgba(52,211,153,0.12)',
        },
        // Accent roles used by charts / status
        accent: {
          blue: '#5b8def',
          purple: '#a78bfa',
          pink: '#f0a4c8',
          yellow: '#eab308',
          orange: '#fb923c',
        },
        // Alert / activity levels (Objective B scale)
        alert: {
          GREEN: '#34d399',
          YELLOW: '#eab308',
          ORANGE: '#fb923c',
          RED: '#f87171',
        },
      },
      borderRadius: {
        xl: '0.9rem',
        '2xl': '1.15rem',
      },
    },
  },
  plugins: [],
}
