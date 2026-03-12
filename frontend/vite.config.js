import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), basicSsl()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    https: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // MJPEG 스트리밍을 위한 타임아웃 비활성화
        timeout: 0,
      },
      '/data': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
