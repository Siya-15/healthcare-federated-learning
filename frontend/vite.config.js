import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Everything under /api is forwarded to the FastAPI backend. The frontend only
// ever speaks HTTP/JSON to the API - it never imports the Python ML modules and
// never downloads a model artifact (see Objective E spec, section 13).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
