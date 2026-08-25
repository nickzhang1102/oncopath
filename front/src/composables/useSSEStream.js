import { ref } from 'vue'

/**
 * SSE 流超时错误（心跳超时/总超时）
 * 用于区分"服务器无响应导致的流中断"（应重试或向调用方报错）
 * 与"用户主动取消"（AbortError，静默退出）
 */
class SSETimeoutError extends Error {
  constructor(message) {
    super(message)
    this.name = 'SSETimeoutError'
  }
}

/**
 * SSE 流处理 composable
 * 统一封装 ReadableStream 读取、JSON 解析、AbortController 管理
 *
 * @param {Function} eventHandler - 接收解析后的事件对象
 * @param {Object} options - 配置选项
 * @param {number} options.maxRetries - 最大重试次数，默认 3
 * @param {number} options.heartbeatTimeout - 心跳超时时间（ms），默认不检测
 * @param {number} options.totalTimeout - 总超时时间（ms），默认不限制
 * @param {string} options.heartbeatEvent - 心跳事件类型名，默认 'heartbeat'
 * @param {string} options.eventTypeField - 事件类型字段名，默认 'type'（上传报告 SSE 用 'status'）
 * @returns {{ startStream, abort, isStreaming, lastHeartbeatTime }}
 */
export function useSSEStream(eventHandler, options = {}) {
  const {
    maxRetries = 3,
    heartbeatTimeout,
    totalTimeout,
    heartbeatEvent = 'heartbeat',
    eventTypeField = 'type',
    heartbeatInterval = 15000
  } = options

  const isStreaming = ref(false)
  const lastHeartbeatTime = ref(null)
  let abortController = null
  let heartbeatTimer = null
  let lastChunkTime = 0

  /**
   * 启动心跳监控定时器（超时以 SSETimeoutError 中止流，走错误处理而非静默取消）
   */
  function startHeartbeatMonitor() {
    stopHeartbeatMonitor()
    heartbeatTimer = setInterval(() => {
      if (heartbeatTimeout && Date.now() - lastChunkTime > heartbeatTimeout) {
        abort(new SSETimeoutError(`心跳超时：${Math.round(heartbeatTimeout / 1000)} 秒内未收到服务器数据`))
      }
    }, heartbeatInterval)
  }

  /**
   * 停止心跳监控定时器
   */
  function stopHeartbeatMonitor() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  /**
   * 处理 SSE 流数据
   */
  async function processStream(response, onData) {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    let buffer = ''
    let dataReceived = false
    const totalDeadline = totalTimeout ? Date.now() + totalTimeout : null

    try {
      while (true) {
        // 检查总超时
        if (totalDeadline && Date.now() > totalDeadline) {
          throw new SSETimeoutError('操作超时')
        }

        const { done, value } = await reader.read()
        if (done) break

        lastChunkTime = Date.now()

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          // SSE 协议中 event: 和 data: 是独立的行类型，当前仅处理 data: 行
          // 事件类型通过 JSON 中的 type 字段判断，而非 SSE event: 字段
          if (!trimmed || trimmed.startsWith('event:')) continue
          if (!trimmed.startsWith('data: ')) continue

          const jsonStr = trimmed.slice(6)
          if (!jsonStr) continue

          try {
            const data = JSON.parse(jsonStr)
            // 心跳事件：更新心跳时间并在内部消费，不传递给 eventHandler
            if (data[eventTypeField] === heartbeatEvent) {
              lastHeartbeatTime.value = Date.now()
              continue
            }
            eventHandler(data)
            if (!dataReceived) {
              dataReceived = true
              onData?.()
            }
          } catch (e) {
            // JSON 解析失败，可能是分段数据或不完整事件
            console.warn('SSE JSON 解析失败:', jsonStr.substring(0, 100), e)
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  }

  /**
   * 启动 SSE 流请求
   * @param {string} url - 请求地址
   * @param {Object} fetchOptions - fetch 选项
   */
  async function startStream(url, fetchOptions = {}) {
    // 终止之前的流
    abort()

    let retryCount = 0
    let hasReceivedData = false

    // 使用 do...while 确保首次请求总是执行
    // maxRetries 控制的是"重试次数"，首次请求不算重试
    do {
      // 首次请求，或上一轮因超时中止被置空后，重建控制器
      if (!abortController) {
        abortController = new AbortController()
        isStreaming.value = true
      }
      lastHeartbeatTime.value = Date.now()
      lastChunkTime = Date.now()
      startHeartbeatMonitor()

      try {
        const response = await fetch(url, {
          ...fetchOptions,
          signal: abortController.signal
        })

        if (!response.ok) {
          // 尝试读取后端返回的 detail 信息
          let detail = ''
          try {
            const body = await response.json()
            detail = body.detail || ''
          } catch { /* 响应体非 JSON，忽略 */ }
          throw new Error(detail || `HTTP ${response.status}: ${response.statusText}`)
        }

        await processStream(response, () => { hasReceivedData = true })
        stopHeartbeatMonitor()
        break // 成功完成，退出循环

      } catch (error) {
        stopHeartbeatMonitor()

        // 超时属于流异常，走下方重试/抛错路径；仅用户主动取消静默退出
        const isTimeout = error instanceof SSETimeoutError || error?.name === 'SSETimeoutError'

        // 用户主动取消，不重试
        if (!isTimeout && error.name === 'AbortError') {
          break
        }

        // 已收到数据后不重试（避免重复请求）
        if (hasReceivedData) {
          console.warn('SSE 流在接收数据后中断，不重试以避免重复请求')
          throw error
        }

        // 检查是否还有重试次数
        if (retryCount >= maxRetries) {
          throw error
        }

        retryCount++
        // 指数退避：2秒、4秒、8秒
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, retryCount) * 1000))
      }
    } while (true)

    isStreaming.value = false
    abortController = null
  }

  /**
   * 终止当前流
   * @param {Error} [reason] - 中止原因；传入 SSETimeoutError 时 fetch 以该错误 reject
   */
  function abort(reason) {
    stopHeartbeatMonitor()
    if (abortController) {
      abortController.abort(reason)
      abortController = null
    }
    isStreaming.value = false
  }

  return {
    startStream,
    abort,
    isStreaming,
    lastHeartbeatTime
  }
}
