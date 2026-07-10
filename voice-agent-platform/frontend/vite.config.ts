import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Docker/Nginx uses "/"; GitHub Pages project site uses "/AI/"
const base = process.env.VITE_BASE_PATH ?? '/AI/'

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
