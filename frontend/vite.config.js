import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/analyze': 'http://127.0.0.1:8000',
      '/compare': 'http://127.0.0.1:8000',
      '/report': 'http://127.0.0.1:8000',
      '/benchmarks': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/explain': 'http://127.0.0.1:8000',

      // Quand le front appelle /stats, on le redirige vers /dashboard/stats du back
      '/stats': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/stats/, '/dashboard/stats')
      },

      // Quand le front appelle /history, on le redirige vers /dashboard/logs du back
      '/history': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/history/, '/dashboard/logs')
      },

      // Quand le front appelle /export, on le redirige vers /dashboard/export du back
      '/export': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/export/, '/dashboard/export')
      },

      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
})