import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Everything under /api is forwarded to the FastAPI backend, so the
    // frontend only ever speaks HTTP/JSON to the API - never to Postgres
    // or the Python ML modules directly.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
