// front/src/composables/useAppVersion.js
// 应用版本号获取：单一权威源为后端 config.APP_VERSION，经公开 /health 端点下发
import { ref } from 'vue'
import axios from 'axios'

// 模块级缓存：版本号在一次页面生命周期内不变，只请求一次
const version = ref('')
let pending = null

function fetchVersion() {
  if (version.value) return Promise.resolve(version.value)
  if (!pending) {
    // 公开端点无需认证，用独立 axios 调用避免走认证拦截器
    pending = axios.get('/api/v1/health', { timeout: 5000 })
      .then((res) => {
        version.value = res.data?.version || ''
        return version.value
      })
      .catch(() => '')
  }
  return pending
}

export function useAppVersion() {
  return { version, fetchVersion }
}
