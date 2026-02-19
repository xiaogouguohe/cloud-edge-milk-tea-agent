import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { apiLoggerPlugin } from './vite-plugin-api-logger'

export default defineConfig({
  plugins: [react(), apiLoggerPlugin()],
  server: {
    port: 5173,
    // /api 代理由 apiLoggerPlugin 接管（含访问日志 + 回源日志），此处不再配置 proxy
  },
})
