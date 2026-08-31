/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        alert: {
          GREEN: '#16a34a',
          YELLOW: '#ca8a04',
          ORANGE: '#ea580c',
          RED: '#dc2626',
        },
      },
    },
  },
  plugins: [],
}
