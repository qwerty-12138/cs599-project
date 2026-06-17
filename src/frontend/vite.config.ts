import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3002,
    proxy: {
      '/api': {
        target: 'http://localhost:8765',
        changeOrigin: true,
        // 对 SSE 流式请求设置长超时
        timeout: 300000,
        proxyTimeout: 300000,
        // 禁用代理缓冲，确保流式数据实时转发
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes, req, res) => {
            // 对 SSE 响应禁用缓冲
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              proxyRes.headers['cache-control'] = 'no-cache'
              proxyRes.headers['x-accel-buffering'] = 'no'
            }
          })
        }
      }
    }
  }
})