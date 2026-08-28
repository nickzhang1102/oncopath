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
  build: {
    // echarts(620kB) 与 export(html2canvas+jsPDF, 588kB) 均为按需加载的异步路由 chunk，
    // 不影响首屏；仅因超过默认 500kB 告警线而提示，放宽到 700kB。
    chunkSizeWarningLimit: 700,
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
    port: 3001,
    allowedHosts: true,  // 开发环境允许所有域名（生产由 Nginx 处理）
    proxy: {
      // AgentTeams 同站反代（与 front/nginx.conf 的 /agentteams 规则一致）。
      // 嵌入页及其 API 均挂在该前缀下：页面走 /agentteams/embed/...，
      // API 走 /agentteams/api/integrations/...，一条规则同时覆盖。
      '/agentteams/': {
        target: 'http://localhost:8380',
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/agentteams/, ''),
      },
      // AgentTeams 嵌入页引用的根路径静态资源（其 Vite 构建产物默认为 /assets/*）
      '/assets/': {
        target: 'http://localhost:8380',
        changeOrigin: true,
      },
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
