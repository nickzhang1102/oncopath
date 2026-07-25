import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import pinia from './stores'

// Vant 样式
import 'vant/lib/index.css'

// Vant 主题配置
import { vantTheme } from '@/styles/vant-theme'

// 全局样式
import '@/styles/index.css'

// 创建应用实例
const app = createApp(App)

// Vant 组件通过 unplugin-vue-components/VantResolver 自动导入，无需手动注册

// 使用插件
app.use(pinia)
app.use(router)

// 应用 Vant 主题
app.provide('vantTheme', vantTheme)

// 全局错误处理
import { setupErrorHandlers } from '@/utils/errorHandler'
setupErrorHandlers(app)

// 挂载应用
app.mount('#app')