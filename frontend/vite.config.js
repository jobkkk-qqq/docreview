import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const sslDir = path.resolve(__dirname, '../backend/ssl')

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [vue()],
  build: {
    target: 'es2015',
    minify: false,
    sourcemap: false,
    emptyOutDir: true,
  },
  server: command === 'serve' ? {
    host: '0.0.0.0',
    port: 3000,
    https: {
      key: fs.readFileSync(path.resolve(sslDir, 'key.pem')),
      cert: fs.readFileSync(path.resolve(sslDir, 'cert.pem')),
    },
    // API 代理配置，将 /api 开头的请求转发到后端服务
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9002',
        changeOrigin: true,
        // 重写重定向 Location 头，防止浏览器跟随重定向到后端直连地址
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes, req, res) => {
            if (proxyRes.statusCode >= 300 && proxyRes.statusCode < 400 && proxyRes.headers.location) {
              const location = proxyRes.headers.location
              // 将后端地址替换为前端代理地址
              proxyRes.headers.location = location.replace(
                'http://127.0.0.1:8000',
                ''
              )
            }
          })
        }
      }
    }
  } : undefined
}))
