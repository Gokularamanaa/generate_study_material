import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../static',
    emptyOutDir: true
  },
  server: {
    port: 3000,
    proxy: {
      '/generate-study-material': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
      '/output': 'http://localhost:8000'
    }
  }
})

