import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages project site: https://subasah.github.io/AI/
const base = process.env.VITE_BASE_PATH || '/AI/'

export default defineConfig({
  base,
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8080',
      '/voice': 'http://localhost:8080',
    },
  },
})
