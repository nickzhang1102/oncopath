import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { VantResolver } from '@vant/auto-import-resolver'
import { vantTheme } from './src/styles/vant-theme'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    vue(),
    Components({
      resolvers: [VantResolver()],
    }),
  ],
  css: {
    preprocessorOptions: {
      less: {
        modifyVars: vantTheme,
        javascriptEnabled: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  optimizeDeps: {
    include: [
      'vue',
      'vue-router',
      'pinia',
      'vant',
      'vant/es',
      'axios',
      'dayjs',
      'echarts',
      'marked',
      'dompurify',
      'html2canvas',
      'jspdf',
      'html2pdf.js',
      'highlight.js',
    ],
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: true,  // 开发环境允许所有域名（生产由 Nginx 处理）
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // SSE 流式响应需要禁用超时和缓冲
        timeout: 0,
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            // SSE 响应禁用压缩和缓冲
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              proxyRes.headers['cache-control'] = 'no-cache'
              proxyRes.headers['x-accel-buffering'] = 'no'
            }
          })
        },
      },
    },
  },
})
