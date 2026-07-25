import axios from 'axios'
import { useUserStore } from '@/stores/user'
import { showToast } from 'vant'
import { getFriendlyErrorMessage } from '@/utils/errorHandler'

// 创建 axios 实例
const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// Token 刷新锁：防止并发 401 触发多次刷新
let isRefreshing = false
let refreshSubscribers = []
// 防止重复跳转登录页
let isRedirectingToLogin = false

function subscribeTokenRefresh(onSuccess, onFail) {
  refreshSubscribers.push({ onSuccess, onFail })
}

function onTokenRefreshed(newToken) {
  refreshSubscribers.forEach(({ onSuccess }) => onSuccess(newToken))
  refreshSubscribers = []
}

function onRefreshFailed() {
  refreshSubscribers.forEach(({ onFail }) => onFail(new Error('Token refresh failed')))
  refreshSubscribers = []
}

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // _skipAuth 标记的请求（如 token 刷新）不注入 access token
    if (!config._skipAuth) {
      const userStore = useUserStore()
      if (userStore.token) {
        config.headers.Authorization = `Bearer ${userStore.token}`
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    return response.data
  },
  async (error) => {
    const { response, config } = error

    // 401 未授权处理
    if (response?.status === 401) {
      // 已在跳转登录页，直接拒绝所有后续 401 请求
      if (isRedirectingToLogin) {
        return Promise.reject(error)
      }

      const errorDetail = response?.data?.detail || ''

      // 特殊处理单点登录冲突
      if (errorDetail.includes('已在其他设备登录') || errorDetail.includes('Token已被撤销')) {
        isRedirectingToLogin = true
        const userStore = useUserStore()
        userStore.logout(true)

        showToast({
          message: '您的账号已在其他设备登录，请重新登录',
          duration: 3000
        })

        setTimeout(() => {
          window.location.href = '/login'
        }, 1500)

        return Promise.reject(error)
      }

      // 其他401错误，尝试刷新 token
      if (!config._retry && !config.url.includes('/auth/refresh')) {
        config._retry = true

        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            subscribeTokenRefresh(
              (newToken) => {
                config.headers.Authorization = `Bearer ${newToken}`
                resolve(request(config))
              },
              (err) => {
                reject(err)
              }
            )
          })
        }

        isRefreshing = true

        try {
          const userStore = useUserStore()
          const data = await request.post('/auth/refresh', null, {
            headers: {
              Authorization: `Bearer ${userStore.refreshToken}`,
            },
            _skipAuth: true
          })
          userStore.setToken(data.access_token, data.refresh_token)

          onTokenRefreshed(data.access_token)

          config.headers.Authorization = `Bearer ${data.access_token}`
          return request(config)
        } catch (refreshError) {
          onRefreshFailed()
          isRedirectingToLogin = true
          const userStore = useUserStore()
          userStore.logout(true)
          window.location.href = '/login'
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      } else {
        // refresh 也失败，或已重试过，直接跳转登录
        isRedirectingToLogin = true
        const userStore = useUserStore()
        userStore.logout(true)
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }

    // 429 限流
    if (response?.status === 429) {
      showToast({ message: '操作过于频繁，请稍后重试', position: 'top' })
      error.handled = true
      return Promise.reject(error)
    }

    // 其他错误使用统一的友好消息（排除已处理的 401）
    if (!error.handled && !config?.silentError) {
      const friendlyMsg = getFriendlyErrorMessage(error)
      showToast(friendlyMsg)
      error.handled = true
    }

    return Promise.reject(error)
  }
)

// 重置 401 跳转标志（用户重新登录后调用）
export function resetRedirectFlag() {
  isRedirectingToLogin = false
}

export default request
