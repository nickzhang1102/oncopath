/**
 * 全局错误处理工具
 * 统一处理 Vue 组件错误、未捕获异常和 API 错误
 */
import { showToast, showFailToast } from 'vant'
import { isAxiosError } from 'axios'

// 错误上报队列（防抖）
const errorQueue = []
let reportTimer = null

/**
 * 注册全局错误处理器
 * 在 main.js 中调用：import { setupErrorHandlers } from '@/utils/errorHandler'; setupErrorHandlers(app)
 */
export function setupErrorHandlers(app) {
  // Vue 组件错误
  app.config.errorHandler = (err, instance, info) => {
    console.error('[Vue Error]', info, err)
    // 不显示过于技术性的错误给用户
    if (!isAxiosError(err)) {
      showFailToast('操作失败，请重试')
    }
    queueError(err, { source: 'vue', info })
  }

  // 未捕获的 JS 异常
  window.onerror = (message, source, lineno, colno, error) => {
    console.error('[Window Error]', message, source, lineno, colno, error)
    queueError(error || new Error(message), { source: 'window', source: source, lineno, colno })
  }

  // 未处理的 Promise rejection
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    console.error('[Unhandled Rejection]', reason)
    // 避免重复处理 axios 错误（axios 拦截器已处理）
    if (!isAxiosError(reason) && !reason?.handled) {
      showFailToast('操作失败，请重试')
    }
    queueError(reason, { source: 'unhandledrejection' })
  })

  // 网络状态监听
  window.addEventListener('offline', () => {
    showToast({ message: '网络连接已断开', position: 'top', duration: 3000 })
  })

  window.addEventListener('online', () => {
    showToast({ message: '网络已恢复', type: 'success', position: 'top', duration: 2000 })
  })
}

/**
 * 判断是否为网络错误
 */
export function isNetworkError(error) {
  return isAxiosError(error) && !error.response && error.code !== 'ECONNABORTED'
}

/**
 * 判断是否为超时错误
 */
export function isTimeoutError(error) {
  return isAxiosError(error) && error.code === 'ECONNABORTED'
}

/**
 * 获取用户友好的错误消息
 */
export function getFriendlyErrorMessage(error) {
  if (isNetworkError(error)) {
    return '网络连接失败，请检查网络'
  }
  if (isTimeoutError(error)) {
    return '请求超时，请稍后重试'
  }
  if (isAxiosError(error)) {
    const status = error.response?.status
    const data = error.response?.data

    // 优先使用服务端返回的错误消息
    if (data?.detail) {
      if (typeof data.detail === 'string') return data.detail
      if (typeof data.detail === 'object' && data.detail?.message) return data.detail.message
      // FastAPI 422 校验错误数组: [{msg, loc, type}, ...]
      if (Array.isArray(data.detail)) {
        const messages = data.detail.map(e => {
          const field = e.loc?.slice(1).join('.') || ''
          return field ? `${field}: ${e.msg}` : e.msg
        })
        return messages.join('; ')
      }
      return JSON.stringify(data.detail)
    }

    switch (status) {
      case 400: return '请求参数错误'
      case 401: return '登录已过期，请重新登录'
      case 403: return '没有权限执行此操作'
      case 404: return '请求的资源不存在'
      case 409: return '数据冲突，请刷新后重试'
      case 422: return '数据格式错误'
      case 429: return '操作过于频繁，请稍后重试'
      case 500: return '服务器内部错误'
      case 502: return '服务暂时不可用'
      case 503: return '服务维护中，请稍后重试'
      case 504: return '请求超时，请稍后重试'
      default: return `请求失败 (${status})`
    }
  }

  return error?.message || '未知错误'
}

/**
 * 将错误加入上报队列（防抖批量上报）
 */
function queueError(error, context) {
  errorQueue.push({
    message: error?.message || String(error),
    stack: error?.stack?.substring(0, 500),
    context,
    timestamp: new Date().toISOString(),
  })

  if (!reportTimer) {
    reportTimer = setTimeout(() => {
      reportTimer = null
      // 后续可接入错误上报服务
      if (errorQueue.length > 0) {
        console.debug(`[ErrorHandler] ${errorQueue.length} errors queued for report`)
        errorQueue.length = 0
      }
    }, 5000)
  }
}
